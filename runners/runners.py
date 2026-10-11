import asyncio
import copy
import httpx
import json
import mimetypes
import os
import re
import threading
import time
import uuid

from adapters.history_adapters import LocalHistoryAdapter, OsHistoryAdapter
from models.models import is_local_model
from runners.follower import get_active_follower
from utils.utils import (
    _build_tool_calls_pair,
    _build_vector_query,
    _convert_json_tool_calls_to_tags,
    _execute_emulated_tool,
    _get_databank_contexts,
    _get_safe_local_path,
    _normalize_tool_name,
    _parse_emulated_tool_call,
    is_real_user_msg,
)
from variables.settings import (
    FOLLOWERS_DIR,
    LOCAL_SERVER_URL,
    get_local_server_headers,
    is_thinking_enabled,
    DISABLED_THINKING,
)

# Global State
cancelled_saves: set[str] = set()
cancelled_sessions = cancelled_saves
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOOL_TAG_RE = re.compile(r"\[(\w+)\(([\s\S]*?)\)\]")
TOOL_TAG_STRIP_RE = re.compile(r"\[\w+\([\s\S]*?\n?\)\]", flags=re.DOTALL)

# Tools that provide dice/lookup or resolve mechanics requiring follow-up narrative generation
QUERY_TOOLS = {
    "arena_roll_combat",
    "arena_roll_check",
    "arena_roll_initiative",
    "arena_roll_skill",
    "arena_sorcerer_absorb",
    "arena_get_location",
    "arena_get_character_context",
    "arena_take_damage",
    "arena_spend_magicka",
    "arena_spend_stamina",
    "arena_add_item",
}

_http_client: httpx.AsyncClient | None = None
_http_client_loop: asyncio.AbstractEventLoop | None = None


def get_http_client() -> httpx.AsyncClient:
    """Returns a persistent, connection-pooled AsyncClient for the current event loop."""
    global _http_client, _http_client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if (
        _http_client is None
        or _http_client.is_closed
        or _http_client_loop != current_loop
    ):
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
        _http_client_loop = current_loop
    return _http_client


def detect_addressed_speaker(text: str, candidate_ids: list[str], exclude_id: str = None) -> str | None:
    """Detects if text explicitly addresses one of the candidate follower IDs or names."""
    if not text or not candidate_ids:
        return None
    from core.follower_config import _load_card_data
    lower_text = text.lower()
    matches = []

    for pid in candidate_ids:
        if exclude_id and pid == exclude_id:
            continue
        c = _load_card_data(pid)
        name = (c.get("name") or pid).lower()
        parts = [name, pid.lower()]
        first_name = name.split()[0] if name else ""
        if len(first_name) >= 3 and first_name not in parts:
            parts.append(first_name)

        matched = False
        for p in parts:
            for pattern in (
                rf"@{re.escape(p)}\b",
                rf"\b{re.escape(p)}\b",
            ):
                m = re.search(pattern, lower_text)
                if m:
                    matches.append((m.start(), pid))
                    matched = True
                    break
            if matched:
                break

    if matches:
        matches.sort(key=lambda x: x[0])
        return matches[0][1]
    return None


def clean_speaker_response(text: str, speaker_id: str = "game", follower_id: str = None) -> str:
    """Strips leading speaker prefix tag for the active speaker if present."""
    if not text:
        return text

    from core.follower_config import _load_card_data

    sp_card = _load_card_data(speaker_id)
    sp_name = (sp_card.get("name") if sp_card else speaker_id).strip()

    for name_candidate in [sp_name, speaker_id, "The Game", "Game", "Dungeon Master", "DM"]:
        if not name_candidate:
            continue
        for prefix in (f"[{name_candidate}]:", f"{name_candidate}:", f"[{name_candidate}]"):
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()

    return text


def _trim_context_messages(messages: list[dict], max_chars: int = 26000) -> list[dict]:
    """Trims oldest non-system chat messages from context if payload exceeds character budget."""
    if not messages:
        return messages
    total = sum(len(m.get("content", "") or "") for m in messages)
    if total <= max_chars:
        return messages

    sys_msgs = [m for m in messages if m.get("role") == "system"]
    non_sys = [m for m in messages if m.get("role") != "system"]
    sys_chars = sum(len(m.get("content", "") or "") for m in sys_msgs)
    avail = max_chars - sys_chars

    kept = []
    cur = 0
    for m in reversed(non_sys):
        c = len(m.get("content", "") or "")
        if cur + c > avail and kept:
            break
        kept.append(m)
        cur += c
    kept.reverse()
    return sys_msgs + kept


class BaseRunner:
    def __init__(self, app_name: str = "Arena"):
        self.app_name = app_name
        self.save_history: dict = {}
        self.save_memory_state: dict = {}
        self.sessions_history = self.save_history
        self.sessions_memory_state = self.save_memory_state

    def _normalize_save_id(self, save_id: str = None) -> str:
        from core.save_manager import get_active_save_id, _get_clean_name
        if not save_id or save_id == "default":
            return get_active_save_id()
        return _get_clean_name(save_id)

    def _get_memory_meta(self, save_id: str) -> dict:
        """Helper to ensure save memory state exists and is synchronized across active saves."""
        target_save_id = self._normalize_save_id(save_id)
        if target_save_id not in self.save_memory_state:
            try:
                from core.save_manager import read_save
                bundle = read_save(target_save_id)
                if "memory_state" in bundle and isinstance(bundle["memory_state"], dict):
                    self.save_memory_state[target_save_id] = bundle["memory_state"]
            except Exception:
                pass

        meta = self.save_memory_state.setdefault(
            target_save_id,
            {"unsummarized_buffer": [], "recent_chapters": [], "epic_chronicle": "", "last_summarized_turn": 0}
        )
        meta.setdefault("last_summarized_turn", 0)
        if len(meta.get("recent_chapters", [])) > 2:
            meta["recent_chapters"] = meta["recent_chapters"][-2:]
        return meta

    async def _post_llm_request(
        self,
        url: str,
        payload: dict,
        headers: dict,
        timeout: float = 60.0,
        save_id: str | None = None,
        session_id: str | None = None,
    ) -> httpx.Response:
        """Send a request to the selected LLM endpoint with cancellation support."""
        is_local = "127.0.0.1:1234" in url or "localhost:1234" in url
        start_time = time.time()
        max_retry_time, retry_interval = 180.0, 2.0
        target_save_id = save_id or session_id

        def _check_cancellation():
            if target_save_id and target_save_id in cancelled_saves:
                cancelled_saves.discard(target_save_id)
                print(f"[CANCEL] Aborting HTTP request for save {target_save_id}", flush=True)
                raise asyncio.CancelledError("Save run cancelled by user request.")

        # Pre-flight check: ensure local LLM server is booted and ready before making requests
        if is_local:
            from adapters.vram_orchestrator import start_llm_async
            target_model = payload.get("model")
            server_ready = await start_llm_async(target_model)
            if not server_ready:
                raise RuntimeError(f"Local LLM server is offline or failed to start (model: {target_model or 'default'}). Check logs/llama_server.log for details.")

        while True:
            _check_cancellation()

            try:

                client = get_http_client()
                if target_save_id:
                    req_payload = {**payload, "stream": True}
                    req_headers = {**headers, "Accept-Encoding": "identity"}

                    async with client.stream("POST", url, json=req_payload, headers=req_headers, timeout=timeout) as r:
                        if r.status_code == 503 and is_local:
                            await r.aread()
                            if time.time() - start_time < max_retry_time:
                                print(f"[Local LLM] Server is loading model (503). Retrying in {retry_interval}s...", flush=True)
                                await asyncio.sleep(retry_interval)
                                continue

                        if r.status_code != 200:
                            await r.aread()
                            return httpx.Response(status_code=r.status_code, headers=r.headers, content=r.content, request=r.request)

                        content_parts = []
                        async for line in r.aiter_lines():
                            _check_cancellation()

                            line = line.strip()
                            if not line or not line.startswith("data:"):
                                continue

                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                break

                            try:
                                delta = json.loads(data_str).get("choices", [{}])[0].get("delta", {})
                                if content := delta.get("content"):
                                    content_parts.append(content)
                            except Exception:
                                pass

                        mock_data = {
                            "choices": [{"message": {"role": "assistant", "content": "".join(content_parts)}}],
                            "model": payload.get("model", ""),
                        }
                        return httpx.Response(status_code=200, headers=r.headers, content=json.dumps(mock_data).encode("utf-8"), request=r.request)

                response = await client.post(url, json=payload, headers=headers, timeout=timeout)
                if response.status_code == 503 and is_local:
                    if time.time() - start_time < max_retry_time:
                        print(f"[Local LLM] Server is loading model (503). Retrying in {retry_interval}s...", flush=True)
                        await asyncio.sleep(retry_interval)
                        continue

                return response

            except httpx.TimeoutException:
                raise
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                from runners import local_runner

                if is_local and local_runner.check_local_server_status() == "starting" and (time.time() - start_time < max_retry_time):
                    print(f"[Local LLM] Connection failed but server is starting. Retrying in {retry_interval}s...", flush=True)
                    await asyncio.sleep(retry_interval)
                    continue
                raise e

    async def _run_llm_summary_task(self, prompt: str, active_model: str, err_msg: str) -> str:
        """Helper to post summary/distillation requests and parse reasoning blocks out of responses."""
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 512,
        }

        target_model = active_model if (active_model and active_model != "local-llm") else os.getenv("LOCAL_MODEL_NAME")
        if target_model:
            payload["model"] = target_model

        try:
            response = await self._post_llm_request(LOCAL_SERVER_URL, payload, get_local_server_headers(), timeout=180.0)
            if response.status_code == 200:
                raw_text = response.json()["choices"][0]["message"].get("content", "").strip()
                think_pattern = r"(?:<think>|\[think\])[\s\S]*?(?:</think>|\[/think\]|<\/\s*think>|\[\s*/\s*think\s*\]|$)"
                return re.sub(think_pattern, "", raw_text, flags=re.IGNORECASE).strip()

            print(f"Local server error: {response.status_code} - {response.text}", flush=True)
        except Exception as e:
            print(f"Error in summary generation task: {e}", flush=True)

        return err_msg

    async def _generate_local_summary(self, text_to_summarize: str, active_model: str, prior_memories: list | None = None) -> str:
        from runners.follower import get_player_name
        from core.follower_config import get_follower_name

        user_name = get_player_name()
        try:
            follower_name = get_follower_name()
        except Exception:
            follower_name = "Follower"

        prompt_parts = [
            f"Summarize this new chat chapter for {user_name} and {follower_name}.",
            "Keep only decisions, preferences, milestones, relationship changes, and project details.",
            "Write 2 concise sentences, under 300 characters. Do not repeat prior memories.\n", # Reduced limit to protect context budget
        ]

        if prior_memories:
            prompt_parts.append("Excerpts of prior memory chapters:")
            prompt_parts.extend(prior_memories)
            prompt_parts.append("Ensure the new summary advances the timeline without repeating the prior memory chapters above.\n")

        prompt_parts.append(f"NEW CHAT HISTORY FOR INCREMENTAL SUMMARY (NEW CHAPTER):\n{text_to_summarize}\n")
        
        return await self._run_llm_summary_task(
            prompt="\n".join(prompt_parts),
            active_model=active_model,
            err_msg="Memory compaction summary generation failed due to connection error.",
        )

    async def _distill_epic_chronicle(self, text_to_distill: str, active_model: str, prior_epic: str = "") -> str:
        from runners.follower import get_player_name
        from core.follower_config import get_follower_name

        user_name = get_player_name()
        try:
            follower_name = get_follower_name()
        except Exception:
            follower_name = "Follower"

        prompt_parts = [
            f"You are the memory chronicler for the ongoing interaction between {user_name} and {follower_name}.",
        ]

        if prior_epic:
            prompt_parts.append(f"EXISTING CHRONICLE:\n{prior_epic}\n")
            prompt_parts.append("The following is a new chapter to integrate into the chronicle above.")

        prompt_parts.extend([
            "Condense these events into a single cohesive general summary (2 concise paragraphs, max 600 characters).",
            "Retain major milestones, key user preferences, shared history, project decisions, and relationship dynamics.\n",
            f"NEW CHAPTER TO DISTILL:\n{text_to_distill}\n",
            "DISTILLED GENERAL SUMMARY:"
        ])

        return await self._run_llm_summary_task(
            prompt="\n".join(prompt_parts),
            active_model=active_model,
            err_msg="Distillation failed due to connection error.",
        )

    async def _process_memory_pipeline(self, save_id: str, active_model: str, user_text: str, assistant_text: str):
        """Asynchronous post-turn worker handling Step 2 (Chapters) and Step 3 (Epic & RAG)."""
        target_save_id = self._normalize_save_id(save_id)
        meta = self._get_memory_meta(target_save_id)
        history = self.save_history.get(target_save_id, [])

        # Filter to genuine dialogue only — exclude tool events, system injections, and quest/item notifications
        hidden_prefixes = ("tool_", "port_", "quest_", "sys_", "itm_")
        dialogue_messages = [
            msg for msg in history
            if msg.get("role") in ("user", "assistant", "follower")
            and not msg.get("id", "").startswith(hidden_prefixes)
            and not (msg.get("text") or "").startswith(("[SYSTEM:", "[Tool Response from"))
        ]

        # Cluster dialogue into user-led turns (user message + all responses before next user turn)
        turns = []
        current_turn = []
        for msg in dialogue_messages:
            if msg.get("role") == "user":
                if current_turn:
                    turns.append(current_turn)
                current_turn = [msg]
            else:
                if current_turn:
                    current_turn.append(msg)
                else:
                    current_turn = [msg]
        if current_turn:
            turns.append(current_turn)

        total_turns = len(turns)
        last_turn = meta.get("last_summarized_turn", 0)

        # Reset pointer if history was rewound or cleared
        if last_turn > total_turns:
            last_turn = 0
            meta["last_summarized_turn"] = 0

        # Process all unsummarized 12-turn chapters
        while total_turns - last_turn >= 12:
            chapter_turns = turns[last_turn : last_turn + 12]

            formatted_turns = "\n".join(
                f"{'User' if msg.get('role') == 'user' else (msg.get('sender_name') or msg.get('sender_id') or 'Game')}: {(msg.get('text') or msg.get('content') or '')[:1000]}"
                for turn_group in chapter_turns for msg in turn_group
            )

            chapter_summary = await self._generate_local_summary(
                text_to_summarize=formatted_turns,
                active_model=active_model,
                prior_memories=meta.get("recent_chapters", [])
            )

            if chapter_summary and not chapter_summary.startswith("Memory compaction summary generation failed"):
                meta.setdefault("recent_chapters", []).append(chapter_summary)

            meta["last_summarized_turn"] = last_turn + 12
            last_turn = meta["last_summarized_turn"]

        # Maintain at most 2 recent chapters; distill older chapters into the running epic chronicle
        while len(meta.get("recent_chapters", [])) > 2:
            oldest_chapter = meta["recent_chapters"].pop(0)
            epic_summary = await self._distill_epic_chronicle(
                text_to_distill=oldest_chapter,
                active_model=active_model,
                prior_epic=meta.get("epic_chronicle", "")
            )
            if epic_summary and not epic_summary.startswith("Distillation failed"):
                meta["epic_chronicle"] = epic_summary

        self._save_to_disk(target_save_id)


    def _load_temperature_setting(self, default_temp: float = 0.75) -> float:
        return default_temp


    def _sanitize_thinking_tags(self, text: str) -> str:
        pattern = (
            r"(?:<think>|\[think\]|<thought>|\[thought\]|<\|thought\|>|<\|channel\|>thought|<channel\|>thought)"
            r"[\s\S]*?"
            r"(?:</think>|\[/think\]|</thought>|\[/thought\]|<\|thought\|>|<\|channel\|>|<channel\|>|<\/\s*think>|\[\s*/\s*think\s*\]|$)"
        )
        cleaned = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return re.sub(r"<\|channel\|>|<channel\|>", "", cleaned, flags=re.IGNORECASE).strip()

    async def _execute_local_llm_loop(
        self,
        save_id: str = None,
        adapter: LocalHistoryAdapter = None,
        model: str = None,
        rag_context: str = "",
        new_message_text: str = None,
        invocation_id: str = "",
        existing_tool_calls: list = None,
        speaker_id: str = "game",
        session_id: str = None,
    ) -> tuple[str, list]:
        target_save_id = self._normalize_save_id(save_id or session_id)
        from core.save_manager import get_active_follower
        follower_id = get_active_follower(target_save_id)
        max_iterations = 5
        iteration = 0
        all_tool_calls = list(existing_tool_calls) if existing_tool_calls else []
        final_response_text = ""
        target_model = model if (model and model != "local-llm") else os.getenv("LOCAL_MODEL_NAME")

        while iteration < max_iterations:
            iteration += 1

            # --- STAGE 1: LOCAL PREPROCESSING ---
            sys_instructions = self._get_system_instructions(target_save_id, user_message=new_message_text, speaker_id=speaker_id)
            messages = adapter.get_openai_messages(sys_instructions, rag_context, speaker_id=speaker_id)
            messages = _trim_context_messages(messages, max_chars=26000)

            # --- STAGE 2: LOCAL PROCESSING PASS ---
            temperature = self._load_temperature_setting()
            url = LOCAL_SERVER_URL
            headers = get_local_server_headers()

            from variables.settings import is_thinking_enabled, DISABLED_THINKING
            from core.banned_words import get_logit_bias_dict

            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1024,
            }
            if not is_thinking_enabled() and isinstance(DISABLED_THINKING, dict):
                payload.update(DISABLED_THINKING)
            if target_model:
                payload["model"] = target_model

            logit_bias = get_logit_bias_dict(url)
            if logit_bias:
                payload["logit_bias"] = logit_bias

            bot_response_text = ""
            try:
                response = await self._post_llm_request(url, payload, headers, timeout=120.0, save_id=target_save_id)
                if response.status_code == 200:
                    bot_response_text = response.json()["choices"][0]["message"]["content"]
                else:
                    bot_response_text = f"Error: {response.text}"
            except Exception as e:
                # Query engine if external server is offline
                try:
                    from runners import engine_llm
                    if engine_llm.is_loaded():
                        bot_response_text = await asyncio.to_thread(
                            engine_llm.generate_text,
                            messages,
                            temperature,
                            1024
                        )
                except Exception:
                    pass

                if not bot_response_text:
                    bot_response_text = f"Error: Could not connect to LLM ({e}). Ensure local llama-server is running."

            # --- STAGE 3: POST-PROCESSING (TOOLS & CLEANUP) ---
            bot_response_text = self._sanitize_thinking_tags(bot_response_text)
            bot_response_text = _convert_json_tool_calls_to_tags(bot_response_text)

            existing_tool_names = {tc.get("name") for tc in all_tool_calls if tc.get("type") == "call"}
            matches = list(TOOL_TAG_RE.finditer(bot_response_text))

            REFEREE_WORLD_TOOLS = {
                "arena_set_location", "arena_travel", "arena_advance_stage", "arena_set_quest_stage",
                "arena_roll_combat", "arena_roll_check", "arena_roll_initiative", "arena_roll_skill",
                "arena_request_skill_check", "arena_sorcerer_absorb", "arena_actor", "actor",
            }
            if speaker_id != "game":
                # Enforce tool partitioning: followers cannot execute referee or world manipulation tools
                valid_matches = []
                for m in matches:
                    norm_name = _normalize_tool_name(m.group(1))
                    if norm_name in REFEREE_WORLD_TOOLS:
                        bot_response_text = bot_response_text.replace(m.group(0), "", 1)
                    else:
                        valid_matches.append(m)
                matches = valid_matches

            new_matches = [m for m in matches if _normalize_tool_name(m.group(1)) not in existing_tool_names]

            if matches:
                if target_save_id in cancelled_saves:
                    raise asyncio.CancelledError("Save run cancelled by user request.")

                if new_matches:
                    raw_results = []
                    for m in new_matches:
                        res = await asyncio.to_thread(_execute_emulated_tool, m.group(1), m.group(2))
                        raw_results.append(res)

                    results = []
                    for m, (parsed_args, output) in zip(new_matches, raw_results):
                        t_name = _normalize_tool_name(m.group(1))
                        t_args = parsed_args["kwargs"]
                        if t_name == "arena_actor":
                            output_dict = {}
                            if isinstance(output, dict):
                                output_dict = output
                            elif isinstance(output, str):
                                try:
                                    import ast
                                    output_dict = ast.literal_eval(output)
                                except Exception:
                                    pass

                            replacement = ""
                            if output_dict.get("success"):
                                spk = str(t_args.get("speaker") or t_args.get("name") or "NPC").strip()
                                dlg = str(t_args.get("dialogue") or t_args.get("speech") or t_args.get("text") or "").strip()

                                clean_dlg = dlg.strip(' "\'')
                                preceding_text = bot_response_text[:m.start()]
                                already_in_text = bool(clean_dlg and clean_dlg in preceding_text)

                                if not already_in_text and clean_dlg:
                                    replacement = f"\n\n{clean_dlg}\n\n"
                                results.append((t_name, t_args, output))

                            bot_response_text = bot_response_text.replace(m.group(0), replacement, 1)
                        else:
                            results.append((t_name, t_args, output))

                    tool_calls = []
                    for idx, (t_name, t_args, t_output) in enumerate(results):
                        tool_calls.extend(_build_tool_calls_pair(t_name, t_args, t_output, len(all_tool_calls) + idx))
                    all_tool_calls.extend(tool_calls)
                else:
                    results = []
                    tool_calls = []

                clean_text = TOOL_TAG_STRIP_RE.sub("", bot_response_text).strip()
                clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)

                player_is_dead = False
                for t_name, _, t_output in results:
                    if t_name in ("arena_take_damage", "arena_roll_combat"):
                        if isinstance(t_output, dict) and t_output.get("dead"):
                            player_is_dead = True
                        elif isinstance(t_output, str) and ("'dead': True" in t_output or '"dead": true' in t_output):
                            player_is_dead = True

                if not player_is_dead:
                    try:
                        from core.character import load_character
                        sheet = load_character(target_save_id)
                        if sheet and sheet.get("derived", {}).get("hp_current", 1) <= 0:
                            player_is_dead = True
                    except Exception:
                        pass

                if player_is_dead:
                    # Dead characters cannot make action checks; discard pending skill checks
                    results = [r for r in results if r[0] != "arena_request_skill_check"]
                    all_tool_calls = [tc for tc in all_tool_calls if tc.get("name") != "arena_request_skill_check"]
                    tool_calls = [tc for tc in tool_calls if tc.get("name") != "arena_request_skill_check"]
                    clean_text = ""
                    final_response_text = ""

                active_tool_names = {tc.get("name") for tc in all_tool_calls if tc.get("type") == "call"}

                if player_is_dead:
                    needs_continuation = True
                elif not clean_text and results:
                    needs_continuation = "arena_request_skill_check" not in active_tool_names
                else:
                    dice_query_tools = {
                        "arena_roll_combat",
                        "arena_roll_check",
                        "arena_roll_initiative",
                        "arena_roll_skill",
                        "arena_sorcerer_absorb",
                    }
                    has_dice_query = any(t_name in dice_query_tools for t_name, _, _ in results)
                    needs_continuation = has_dice_query and "arena_request_skill_check" not in active_tool_names

                if not results or not needs_continuation:
                    final_response_text = clean_speaker_response(clean_text, speaker_id=speaker_id, follower_id=follower_id)
                    image_tools = {
                        "generate_local_image",
                        "generate_follower_portrait",
                        "generate_player_portrait",
                        "generate_environment_image",
                        "generate_program_portrait",
                        "generate_general_image",
                        "generate_imagen",
                        "apply_comfy_workflow",
                    }
                    if any(t_name in image_tools for t_name in active_tool_names):
                        msg_lower = (new_message_text or "").lower()
                        is_portrait_turn = any(k in msg_lower for k in ("portrait", "draw", "picture", "image", "photo", "selfie", "generate_program_portrait", "generate_local_image", "generate_follower_portrait", "generate_player_portrait", "generate_environment_image"))
                        if is_portrait_turn:
                            final_response_text = ""
                    adapter.append_assistant_message(final_response_text, all_tool_calls, invocation_id, speaker_id=speaker_id)
                    break

                clean_text = clean_speaker_response(clean_text, speaker_id=speaker_id, follower_id=follower_id)
                adapter.append_assistant_message(clean_text, tool_calls, invocation_id, intermediate=True, speaker_id=speaker_id)
                adapter.append_tool_events(results, invocation_id)

                if clean_text:
                    final_response_text = clean_text

                continue
            else:
                clean_text = clean_speaker_response(bot_response_text.strip(), speaker_id=speaker_id, follower_id=follower_id)
                final_response_text = clean_text if clean_text else final_response_text

                adapter.append_assistant_message(final_response_text, all_tool_calls, invocation_id, speaker_id=speaker_id)
                break

        adapter.post_process_thoughts(invocation_id)
        final_response_text = clean_speaker_response(final_response_text, speaker_id=speaker_id, follower_id=follower_id)
        final_response_text = self._ensure_images_are_embedded(final_response_text)

        # Process Memory Pipeline
        await self._process_memory_pipeline(
            save_id=target_save_id,
            active_model=target_model or "",
            user_text=new_message_text,
            assistant_text=final_response_text
        )

        return final_response_text, all_tool_calls
    
    @property
    def saves_dir(self) -> str:
        from core.save_manager import SAVES_DIR
        os.makedirs(SAVES_DIR, exist_ok=True)
        return str(SAVES_DIR)

    @property
    def sessions_dir(self) -> str:
        return self.saves_dir

    async def get_history(self, save_id: str) -> list:
        raise NotImplementedError()

    async def run_async(self, save_id: str, new_message_text: str = None, image_data: str = None, image_mime: str = None, model: str = None, media_path: str = None, msg_id: str = None, existing_tool_calls: list = None, speaker_id: str = "game") -> tuple:
        raise NotImplementedError()

    async def edit_turn(self, save_id: str, msg_id: str, new_text: str = None, model: str = None, force_offload: bool = False, speaker_id: str = None) -> tuple:
        raise NotImplementedError()

    async def reset_save(self, save_id: str):
        raise NotImplementedError()

    async def reset_session(self, session_id: str):
        return await self.reset_save(session_id)

    async def delete_turn(self, save_id: str, msg_id: str) -> bool:
        raise NotImplementedError()

    async def delete_image_from_save(self, save_id: str, image_url: str) -> bool:
        raise NotImplementedError()

    async def delete_image_from_session(self, session_id: str, image_url: str) -> bool:
        return await self.delete_image_from_save(session_id, image_url)

    async def replace_image_in_save(self, save_id: str, old_image_url: str, new_image_url: str) -> bool:
        raise NotImplementedError()

    async def replace_image_in_session(self, session_id: str, old_image_url: str, new_image_url: str) -> bool:
        return await self.replace_image_in_save(session_id, old_image_url, new_image_url)

    async def replace_image_with_video_in_save(self, save_id: str, old_image_url: str, new_video_url: str) -> bool:
        raise NotImplementedError()

    async def replace_image_with_video_in_session(self, session_id: str, old_image_url: str, new_video_url: str) -> bool:
        return await self.replace_image_with_video_in_save(session_id, old_image_url, new_video_url)

    async def append_message_to_save(
        self,
        save_id: str,
        role: str,
        text: str,
        sender_id: str | None = None,
        sender_name: str | None = None,
        tool_calls: list | None = None,
    ) -> dict:
        raise NotImplementedError()

    async def append_message_to_session(
        self,
        session_id: str,
        role: str,
        text: str,
        sender_id: str | None = None,
        sender_name: str | None = None,
        tool_calls: list | None = None,
    ) -> dict:
        return await self.append_message_to_save(
            save_id=session_id,
            role=role,
            text=text,
            sender_id=sender_id,
            sender_name=sender_name,
            tool_calls=tool_calls,
        )

    async def delete_system_memory(self, save_id: str, timestamp: float) -> bool:
        raise NotImplementedError()

    async def update_message_text(self, save_id: str, msg_id: str, new_text: str) -> bool:
        raise NotImplementedError()

    async def delete_message_at(self, save_id: str, msg_id: str) -> bool:
        raise NotImplementedError()

    def _delete_local_image(self, image_url: str) -> bool:
        local_path = _get_safe_local_path(image_url) if image_url else None
        if not local_path or not os.path.exists(local_path):
            return False

        try:
            os.remove(local_path)
            print(f"Deleted image file from disk: {local_path}")

            json_path = os.path.splitext(local_path)[0] + ".json"
            if os.path.exists(json_path):
                os.remove(json_path)
                print(f"Deleted follower JSON file from disk: {json_path}")
            return True
        except Exception as e:
            print(f"Error cleaning up image assets for {image_url}: {e}")
            return False

    def _ensure_images_are_embedded(self, text: str) -> str:
        if not text:
            return text

        text = re.sub(r'(?<!\!)(\[[^\]]*\]\(/images/(?:portraits|media)/[^)]+\))', r'!\1', text)
        raw_path_pattern = r'(?<![\([/])(/images/(?:portraits|media)/[a-zA-Z0-9_\-\.]+\.(?:png|jpg|jpeg|webp|gif|mp4))'
        return re.sub(raw_path_pattern, r'![Portrait](\1)', text)

    def _inject_journals(self, instructions: str, user_message: str) -> str:
        if not user_message:
            return instructions

        try:
            from core.follower_config import replace_placeholders
            from core.journals import match_journals

            if matched_entries := match_journals(user_message, get_active_follower()):
                if "\n\n# RECALLED JOURNALS / MEMORIES\n" not in instructions:
                    instructions += "\n\n# RECALLED JOURNALS / MEMORIES\n"
                for entry in matched_entries:
                    instructions += f"- {replace_placeholders(entry['content'])}\n"
        except Exception as je:
            print(f"Error matching journals: {je}")

        return instructions

    def _inject_system_memories(self, instructions: str, save_id: str) -> str:
        target_save_id = self._normalize_save_id(save_id)
        meta = self._get_memory_meta(target_save_id)
        epic = meta.get("epic_chronicle", "")
        chapters = meta.get("recent_chapters", [])

        # Enforce the limit of only the 2 most recent chapters
        recent_two_chapters = chapters[-2:] if chapters else []

        if epic:
            # Optional: ensure epic stays compact within your ~600 char limit
            instructions += f"\n\n# CORE CONVERSATION CHRONICLE\n{epic.strip()}\n"

        if recent_two_chapters:
            formatted_chapters = "\n".join(f"- {ch.strip()}" for ch in recent_two_chapters)
            instructions += f"\n\n# RECENT CONVERSATION CHAPTERS\n{formatted_chapters}\n"

        return instructions

    def _get_system_instructions(self, save_id: str, user_message: str = None, speaker_id: str = "game") -> str:
        from core.follower_config import compile_speaker_instructions, replace_placeholders, get_follower_name
        from core.save_manager import get_active_followers
        import re

        target_save_id = self._normalize_save_id(save_id)
        party = get_active_followers(target_save_id)
        instructions = compile_speaker_instructions(speaker_id=speaker_id, party_followers=party)

        try:
            from core.world_engine import load_world_state
            from core.character import load_character
            ws = load_world_state(target_save_id)
            loc = ws.get("current_location", "Imperial Dungeon")
            prov = ws.get("current_province", "Cyrodiil")
            q_stage = ws.get("quest_stage", 1)
            sheet = load_character(target_save_id)
            d = sheet.get("derived", {})
            hp_cur, hp_max = d.get("hp_current", 25), d.get("hp_max", 25)
            mp_cur, mp_max = d.get("mp_current", d.get("sp_current", 40)), d.get("mp_max", d.get("sp_max", 40))
            stm_cur, stm_max = d.get("stamina_current", 50), d.get("stamina_max", 50)
            player_name = sheet.get("name", "Eternal Champion")
            party_names_str = ", ".join(get_follower_name(fid) for fid in party) if party else "None (Traveling solo)"

            # Quest objective
            quest_objective = ""
            try:
                from core.quest_tracker import load_quest_stages, get_stage_context_injection
                quest_objective = get_stage_context_injection(ws, load_quest_stages())
            except Exception:
                pass

            # Faction standings (non-zero only)
            faction_pieces = []
            try:
                for fname, val in ws.get("faction_reputation", {}).items():
                    if val != 0:
                        sign = "+" if val > 0 else ""
                        faction_pieces.append(f"{fname} {sign}{val}")
            except Exception:
                pass

            # Follower factions
            try:
                from core.follower_config import _load_card_data
                for fid in party:
                    card = _load_card_data(fid)
                    factions = card.get("factions", [])
                    if factions:
                        follower_label = get_follower_name(fid)
                        faction_pieces.append(f"{follower_label}: {', '.join(factions)}")
            except Exception:
                pass

            faction_str = " | ".join(faction_pieces)

            instructions += (
                f"\n\n# ACTIVE SCENE & WORLD STATE\n"
                f"- Location: {loc}, {prov} (Main Quest Stage {q_stage})"
                + (f"\n- Objective: {quest_objective}" if quest_objective else "")
                + f"\n- Party: {player_name} (HP {hp_cur}/{hp_max}, MP {mp_cur}/{mp_max}, Stamina {stm_cur}/{stm_max}) | Followers: {party_names_str}\n"
                + (f"- Factions: {faction_str}\n" if faction_str else "")
            )
        except Exception as se:
            print(f"Error compiling scene state header: {se}")

        instructions = self._inject_system_memories(instructions, target_save_id)
        instructions = self._inject_journals(instructions, user_message)

        # Image and portrait generation directives
        if user_message and any(k in user_message for k in ("Generate a portrait of yourself", "[GENERATE_IMAGE:", "[GENERATE_IMAGEN:", "[GENERATE_PLAYER_PORTRAIT:", "[GENERATE_ENVIRONMENT:", "[GENERATE_FOLLOWER_PORTRAIT:", "generate_follower_portrait", "generate_player_portrait", "generate_environment_image")):
            msg_lower = user_message.lower()

            # Retrieve recent scene narrative for contextual pose & scenery inference
            recent_scene_snippet = ""
            try:
                history = self.save_history.get(target_save_id, [])
                narrative_msgs = [
                    m for m in history
                    if m.get("role") in ("follower", "assistant", "user")
                    and (m.get("text") or "").strip()
                    and not any(k in (m.get("text") or "") for k in ("[GENERATE_IMAGE", "[GENERATE_IMAGEN", "[GENERATE_PLAYER_PORTRAIT", "[GENERATE_ENVIRONMENT", "[GENERATE_FOLLOWER_PORTRAIT"))
                ]
                if narrative_msgs:
                    recent_snippets = []
                    for nm in narrative_msgs[-2:]:
                        r_name = "User" if nm.get("role") == "user" else (nm.get("sender_name") or "Narrative")
                        t_clean = re.sub(r'<!--.*?-->', '', nm.get("text", "")).strip()
                        if t_clean:
                            recent_snippets.append(f"- {r_name}: {t_clean[:350]}")
                    if recent_snippets:
                        recent_scene_snippet = "\n" + "\n".join(recent_snippets)
            except Exception:
                pass

            context_block = f"\nRecent Scene Dialogue & Actions:{recent_scene_snippet}\n" if recent_scene_snippet else ""

            comp_pieces = []
            try:
                from core.follower_config import get_follower_image_details
                for fid in party:
                    if fid not in ("game", "the_game"):
                        fname = get_follower_name(fid)
                        pos, _ = get_follower_image_details(fid)
                        if pos:
                            comp_pieces.append(f"{fname} (appearance reference: {pos})")
                        else:
                            comp_pieces.append(fname)
            except Exception:
                pass
            comp_context = f"\nCompanions in scene: {'; '.join(comp_pieces)}\n" if comp_pieces else ""

            instructions += (
                f"\n\n# Scene Capture Directive\n"
                f"Generate an image depicting the current scene.{context_block}{comp_context}"
                f"Organize your comma-separated visual tags in clean order:\n"
                f"1. Characters Present: Name each companion present (e.g. '[Name]'), followed immediately by their full character appearance tags and their scene pose or action. Do not describe any viewer, player POV, or camera perspective.\n"
                f"2. Environment & Setting: architecture, room/dungeon geometry, terrain.\n"
                f"3. Lighting & Atmosphere: torchlight, shadows, mood.\n"
                f"Output only the tool call:\n"
                f"`[generate_local_image(prompt=\"[ordered visual tags: characters with appearance tags -> environment -> lighting]\")]`."
            )

        return replace_placeholders(instructions, follower_id=speaker_id, party_followers=party)


BaseProgramRunner = BaseRunner


class OpenSourceRunner(BaseRunner):
    """Operates independently of cloud infrastructure, reading character settings
    directly from the follower's JSON profile.
    """

    def __init__(self, app_name="Arena"):
        super().__init__(app_name)
        self.sessions_history = {}
        self.sessions_memory_state = {}
        self._lock = threading.RLock()

    async def generate_impersonation(
        self, prompt: str, system_instruction: str, model: str = None, temperature: float = 0.7, max_tokens: int = 1536
    ) -> str:
        url = LOCAL_SERVER_URL
        headers = get_local_server_headers()
        target_model = model if (model and model != "local-llm") else os.getenv("LOCAL_MODEL_NAME")

        from core.banned_words import get_logit_bias_dict

        payload = {
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if not is_thinking_enabled() and isinstance(DISABLED_THINKING, dict):
            payload.update(DISABLED_THINKING)
        if target_model:
            payload["model"] = target_model

        logit_bias = get_logit_bias_dict(url)
        if logit_bias:
            payload["logit_bias"] = logit_bias

        r = await self._post_llm_request(url, payload, headers, timeout=60.0)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "").strip()
            pattern = (
                r"(?:<think>|\[think\])[\s\S]*?(?:</think>|\[/think\]|<\/\s*think>|\[\s*/\s*think\s*\]|$)"
            )
            return re.sub(pattern, "", content, flags=re.IGNORECASE).strip()

        raise Exception(f"HTTP Server returned status code {r.status_code}: {r.text}")

    def _get_save_path(self, save_id: str) -> str:
        from core.save_manager import get_save_path
        return str(get_save_path(self._normalize_save_id(save_id)))

    _get_session_path = _get_save_path

    def _save_to_disk(self, save_id: str):
        target_save_id = self._normalize_save_id(save_id)
        with self._lock:
            try:
                from core.save_manager import read_save, write_save
                bundle = read_save(target_save_id)
                bundle["messages"] = self.save_history.get(target_save_id, [])
                bundle["memory_state"] = self.save_memory_state.get(
                    target_save_id,
                    {"unsummarized_buffer": [], "recent_chapters": [], "epic_chronicle": "", "last_summarized_turn": 0}
                )
                write_save(target_save_id, bundle)
            except Exception as e:
                print(f"Error saving save {target_save_id} to disk: {e}")

    _save_session_to_disk = _save_to_disk

    def _load_from_disk(self, save_id: str) -> bool:
        target_save_id = self._normalize_save_id(save_id)
        with self._lock:
            try:
                from core.save_manager import read_save
                bundle = read_save(target_save_id)
                self.save_history[target_save_id] = bundle.get("messages", [])
                memory_state = bundle.get(
                    "memory_state",
                    {"unsummarized_buffer": [], "recent_chapters": [], "epic_chronicle": "", "last_summarized_turn": 0}
                )

                # For saves created before the watermark was added, default to current turn count
                # so the pipeline doesn't re-summarize already-seen history
                if "last_summarized_turn" not in memory_state:
                    history = self.save_history.get(target_save_id, [])
                    dialogue_count = sum(1 for m in history if m.get("role") in ("user", "assistant", "follower"))
                    memory_state["last_summarized_turn"] = dialogue_count // 2

                # Enforce 2-chapter cap on load
                if len(memory_state.get("recent_chapters", [])) > 2:
                    memory_state["recent_chapters"] = memory_state["recent_chapters"][-2:]

                self.save_memory_state[target_save_id] = memory_state
                self._ensure_first_message(target_save_id)
                return True
            except Exception as e:
                print(f"Error loading save {target_save_id} from disk: {e}")
                return False

    _load_session_from_disk = _load_from_disk

    def _ensure_first_message(self, save_id: str):
        target_save_id = self._normalize_save_id(save_id)
        history = self.save_history.setdefault(target_save_id, [])

        has_first_mes = any(
            msg.get("id", "").startswith("first_mes") or (msg.get("role") == "follower" and msg == history[0])
            for msg in history
        )

        if not has_first_mes:
            try:
                from core.follower_config import get_follower_greeting, replace_placeholders
                from runners.follower import get_player_name
                user_name = get_player_name()

                if greeting := replace_placeholders(get_follower_greeting("game"), user_name=user_name).strip():
                    starting_msg = {
                        "id": f"first_mes_{uuid.uuid4().hex}",
                        "role": "follower",
                        "sender_id": "game",
                        "sender_name": "The Game",
                        "text": greeting,
                        "tool_calls": [],
                        "timestamp": time.time(),
                    }
                    history.insert(0, starting_msg)
                    self._save_session_to_disk(save_id)
            except Exception as e:
                print(f"[runner] Could not seed first_mes: {e}")

        updated = False
        for idx, msg in enumerate(history):
            if msg.get("id", "").startswith("first_mes"):
                if not msg.get("sender_id"):
                    msg["sender_id"] = "game"
                    msg["sender_name"] = "The Game"
                    updated = True
                if not msg.get("text") or "I am Ria Silmane" in msg.get("text", ""):
                    from core.follower_config import get_follower_greeting, replace_placeholders
                    from runners.follower import get_player_name
                    user_name = get_player_name()
                    msg["text"] = replace_placeholders(get_follower_greeting("game"), user_name=user_name).strip()
                    msg["sender_id"] = "game"
                    msg["sender_name"] = "The Game"
                    updated = True
            if not msg.get("id"):
                role = msg.get("role", "msg")
                prefix = "first_mes" if role == "follower" and idx == 0 else role
                msg["id"] = f"{prefix}_{uuid.uuid4().hex}"
                if prefix == "first_mes":
                    msg["sender_id"] = "game"
                    msg["sender_name"] = "The Game"
                updated = True

        if updated:
            self._save_session_to_disk(save_id)

    def _consolidate_tools(self, tool_calls: list) -> list:
        if not tool_calls:
            return []

        pairs = {}
        for tc in tool_calls:
            cid = tc.get("id", "")
            if cid not in pairs:
                pairs[cid] = {"id": cid}

            if tc.get("type") == "call":
                pairs[cid]["name"] = tc.get("name", "")
                pairs[cid]["args"] = tc.get("args", {})
            elif tc.get("type") == "response":
                pairs[cid]["result"] = tc.get("response", "")

        return [p for p in pairs.values() if p.get("name")]

    def _extract_media_items(self, text: str, img_url: str, tool_calls: list) -> list:
        media = []
        seen_urls = set()

        def _add_media(url: str):
            if url and url not in seen_urls and not url.startswith("data:"):
                seen_urls.add(url)
                media.append({"url": url, "type": "video" if url.lower().endswith(".mp4") else "image"})

        for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text):
            _add_media(match.group(2))

        _add_media(img_url)

        for tc in tool_calls or []:
            if tc.get("type") == "response" and (resp := tc.get("response")):
                for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", resp):
                    _add_media(match.group(2))

        return media

    def _normalize_message(self, msg: dict) -> dict:
        text = msg.get("text", "") or ""
        tool_calls = msg.get("tool_calls", [])

        media = self._extract_media_items(text, msg.get("image_url"), tool_calls)
        clean_text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text).strip()
        clean_text = clean_text.replace("(Generation stopped)", "").strip()
        tool_summary = self._consolidate_tools(tool_calls)

        image_tools = {
            "generate_local_image",
            "generate_imagen",
            "generate_follower_portrait",
            "generate_player_portrait",
            "generate_environment_image",
            "generate_program_portrait",
            "generate_general_image",
        }
        image_prompt = next(
            (ts.get("args", {}).get("prompt") for ts in tool_summary if ts.get("name") in image_tools),
            None,
        )

        if image_prompt:
            for m in media:
                m.setdefault("prompt", image_prompt)

        role = msg.get("role", "user")
        sender_id = msg.get("sender_id")
        msg_id = msg.get("id", "")
        if not sender_id:
            if role == "user":
                sender_id = "user"
            elif msg_id.startswith("game_") or msg_id.startswith("first_mes"):
                sender_id = "game"
            elif msg_id.startswith("fol_"):
                parts = msg_id.split("_")
                sender_id = parts[1] if len(parts) > 1 else "game"
            else:
                sender_id = "game"

        follower_id = msg.get("follower_id")
        if not follower_id and sender_id not in ("game", "user"):
            follower_id = sender_id

        sender_name = msg.get("sender_name")
        if not sender_name:
            if sender_id == "game":
                sender_name = "The Game"
            elif sender_id == "user":
                sender_name = "Hero"
            else:
                try:
                    from core.follower_config import get_follower_name
                    sender_name = get_follower_name(sender_id)
                except Exception:
                    sender_name = "Follower"

        return {
            "id": msg_id,
            "role": role,
            "sender_id": sender_id,
            "follower_id": follower_id,
            "sender_name": sender_name,
            "text": clean_text,
            "media": media,
            "tool_summary": tool_summary,
            "tool_calls": tool_calls,
            "timestamp": msg.get("timestamp"),
            "editable": role in ("user", "follower"),
            "deletable": True,
        }

    async def get_history(self, save_id: str = None, session_id: str = None) -> list:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            self._load_from_disk(target_save_id)
            self._ensure_first_message(target_save_id)

            raw_history = self.save_history.get(target_save_id, [])
            updated_any = False

            for msg in raw_history:
              if updated_any:
                self._save_to_disk(target_save_id)

            hidden_prefixes = ("tool_", "port_", "quest_", "sys_", "itm_")
            chat_history = []

            for msg in raw_history:
                if msg.get("role") == "system-memory" or msg.get("id", "").startswith(hidden_prefixes):
                    continue
                if msg.get("role") == "follower":
                    if not (msg.get("text") or "").strip() and not msg.get("tool_calls"):
                        continue
                chat_history.append(self._normalize_message(msg))

            return chat_history

    async def run_async(
        self,
        save_id: str = None,
        new_message_text: str = None,
        image_data: str = None,
        image_mime: str = None,
        model: str = None,
        media_path: str = None,
        msg_id: str = None,
        existing_tool_calls: list = None,
        speaker_id: str = "game",
        session_id: str = None,
    ) -> tuple:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            self._load_from_disk(target_save_id)
            self.save_history.setdefault(target_save_id, [])

            try:
                return await self._run_async_internal(
                    save_id=target_save_id,
                    new_message_text=new_message_text,
                    image_data=image_data,
                    image_mime=image_mime,
                    model=model,
                    media_path=media_path,
                    msg_id=msg_id,
                    existing_tool_calls=existing_tool_calls,
                    speaker_id=speaker_id,
                )
            finally:
                self._save_to_disk(target_save_id)

    async def _run_async_internal(
        self,
        save_id: str = None,
        new_message_text: str = None,
        image_data: str = None,
        image_mime: str = None,
        model: str = None,
        media_path: str = None,
        msg_id: str = None,
        existing_tool_calls: list = None,
        speaker_id: str = "game",
        session_id: str = None,
    ) -> tuple:
        target_save_id = self._normalize_save_id(save_id or session_id)
        if target_save_id not in self.save_history:
            self._load_from_disk(target_save_id)

        self._ensure_first_message(target_save_id)

        file_path_resolved = None
        if media_path and media_path.startswith("/images/"):
            try:
                rel_path = media_path[len("/images/") :]
                local_file_path = os.path.normpath(os.path.join(project_root, "core", "FOLLOWERS", get_active_follower(), rel_path))
                if os.path.exists(local_file_path):
                    mime_type, _ = mimetypes.guess_type(local_file_path)
                    if mime_type and mime_type.startswith("image/"):
                        file_path_resolved = local_file_path
            except Exception as e:
                print(f"Error handling media_path in OpenSourceRunner: {e}")

        user_msg_id = None
        if new_message_text or image_data or media_path:
            if not msg_id:
                raw_text = new_message_text or ""
                if raw_text.startswith("[SYSTEM: User has completed"):
                    prefix = "quest_"
                elif any(k in raw_text for k in ("Generate a portrait of yourself", "[GENERATE_IMAGE:", "[GENERATE_IMAGEN:", "generate_follower_portrait")):
                    prefix = "port_"
                elif raw_text.startswith("[Tool Response from"):
                    prefix = "tool_"
                elif (media_path or image_data) and not raw_text.strip():
                    prefix = "img_"
                else:
                    prefix = "usr_"
                user_msg_id = f"{prefix}{uuid.uuid4().hex}"
            else:
                user_msg_id = msg_id

            from core.world_engine import load_world_state, create_state_snapshot
            from core.character import load_character
            user_snapshot = create_state_snapshot(load_world_state(target_save_id), load_character(target_save_id))

            user_msg = {
                "id": user_msg_id,
                "role": "user",
                "text": new_message_text or "",
                "image_url": media_path if media_path else (f"data:{image_mime};base64,{image_data}" if image_data else None),
                "timestamp": time.time(),
                "state_snapshot": user_snapshot,
            }
            self.save_history[target_save_id].append(user_msg)

        history = self.save_history.get(target_save_id, [])
        vector_query = _build_vector_query(history)
        rag_context, query_vector_embedding = _get_databank_contexts(vector_query)

        adapter = OsHistoryAdapter(
            self, target_save_id, file_path_resolved, image_data, image_mime, query_vector=query_vector_embedding
        )

        res = await self._execute_local_llm_loop(
            save_id=target_save_id,
            adapter=adapter,
            model=model,
            rag_context=rag_context,
            new_message_text=new_message_text or "",
            invocation_id="",
            existing_tool_calls=existing_tool_calls,
            speaker_id=speaker_id,
        )

        bot_response_text, tool_calls = res

        history = self.save_history.get(target_save_id, [])
        target_speaker = speaker_id or "game"
        follower_msg_id = None
        if history and history[-1].get("role") == "follower" and history[-1].get("sender_id", "game") == target_speaker:
            follower_msg_id = history[-1].get("id")
        else:
            follower_msg_id = next(
                (m.get("id") for m in reversed(history) if m.get("role") == "follower" and m.get("sender_id", "game") == target_speaker),
                None
            )

        return bot_response_text, tool_calls, user_msg_id, follower_msg_id

    async def edit_turn(
        self, save_id: str = None, msg_id: str = None, new_text: str = None, model: str = None, force_offload: bool = False, speaker_id: str = None, session_id: str = None
    ) -> tuple:
        target_save_id = self._normalize_save_id(save_id or session_id)
        if target_save_id not in self.save_history:
            self._load_from_disk(target_save_id)

        history = self.save_history.get(target_save_id)
        if not history:
            raise ValueError("Save not found")

        user_idx = next((i for i, ev in enumerate(history) if ev.get("id") == msg_id), -1)
        if user_idx == -1:
            raise ValueError("Message not found")

        # Restrict rerolling to the last turn in chat (ignoring tool responses)
        subsequent_users = [
            ev for ev in history[user_idx + 1:]
            if ev.get("role") == "user"
            and not ev.get("id", "").startswith("tool_")
            and not ev.get("text", "").startswith("[Tool Response from")
        ]
        if subsequent_users:
            raise ValueError("Only the last message in chat can be rerolled.")

        orig_msg = history[user_idx]
        img_data, img_mime, media_path = None, None, None

        if url_str := orig_msg.get("image_url"):
            if url_str.startswith("data:") and ";base64," in url_str:
                parts = url_str.split(";base64,")
                img_mime = parts[0].split("data:")[-1]
                img_data = parts[1]
            else:
                media_path = url_str

        # Roll back game state and tool effects for all discarded subsequent messages
        prior_snapshot = orig_msg.get("state_snapshot")
        if prior_snapshot:
            from core.world_engine import apply_state_snapshot
            apply_state_snapshot(target_save_id, prior_snapshot)
        else:
            discarded_tools = []
            for subsequent_msg in history[user_idx + 1:]:
                if subsequent_msg.get("tool_calls"):
                    discarded_tools.extend(subsequent_msg["tool_calls"])
            if discarded_tools:
                from core.character import rollback_tool_effects
                rollback_tool_effects(target_save_id, discarded_tools)

        self.save_history[target_save_id] = history[:user_idx]
        self._save_to_disk(target_save_id)

        new_input = new_text if new_text is not None else orig_msg.get("text", "")
        if not speaker_id:
            from core.save_manager import get_active_followers
            from app import determine_first_speaker
            active_fols = get_active_followers(target_save_id)
            speaker_id = determine_first_speaker(new_input, history[:user_idx], active_fols)
        res = await self.run_async(
            save_id=target_save_id,
            new_message_text=new_input,
            image_data=img_data,
            image_mime=img_mime,
            model=model,
            media_path=media_path,
            msg_id=msg_id,
            existing_tool_calls=None,
            speaker_id=speaker_id,
        )

        self._save_to_disk(target_save_id)
        return res

    async def reroll_message(
        self, save_id: str = None, msg_id: str = None, model: str = None, session_id: str = None
    ) -> tuple:
        target_save_id = self._normalize_save_id(save_id or session_id)
        if target_save_id not in self.save_history:
            self._load_from_disk(target_save_id)

        history = self.save_history.get(target_save_id)
        if not history:
            raise ValueError("Save not found")

        msg_idx = next((i for i, ev in enumerate(history) if ev.get("id") == msg_id), -1)
        if msg_idx == -1:
            raise ValueError(f"Message {msg_id} not found")

        hidden_prefixes = ("tool_", "port_", "quest_", "sys_", "itm_")
        visible_indices = [
            i for i, ev in enumerate(history)
            if not ev.get("id", "").startswith(hidden_prefixes) and ev.get("role") != "system-memory"
        ]
        if visible_indices and msg_idx != visible_indices[-1]:
            raise ValueError("Only the last message in chat can be rerolled.")

        target_msg = history[msg_idx]
        speaker_id = target_msg.get("sender_id")
        if not speaker_id:
            mid = target_msg.get("id", "")
            if mid.startswith("game_") or mid.startswith("first_mes"):
                speaker_id = "game"
            elif mid.startswith("fol_"):
                parts = mid.split("_")
                speaker_id = parts[1] if len(parts) > 1 else "game"
            else:
                from runners.follower import get_active_follower
                speaker_id = get_active_follower() or "game"

        # Determine the start of this assistant turn (including intermediate and tool event messages)
        turn_start_idx = msg_idx
        while turn_start_idx > 0:
            prev = history[turn_start_idx - 1]
            pid = prev.get("id", "")
            prole = prev.get("role", "")
            ptext = prev.get("text", "")
            if pid.startswith(("tool_", "itm_")) or (prole == "user" and ptext.startswith("[Tool Response from")):
                turn_start_idx -= 1
            else:
                break

        # Preserve any messages subsequent to this turn
        subsequent_messages = list(history[msg_idx + 1:])
        discarded_messages = list(history[turn_start_idx:msg_idx + 1])

        # Roll back game state and character mutations from the turn being rerolled
        prior_msg = history[turn_start_idx - 1] if turn_start_idx > 0 else None
        prior_snapshot = prior_msg.get("state_snapshot") if prior_msg else None
        if prior_snapshot:
            from core.world_engine import apply_state_snapshot
            apply_state_snapshot(target_save_id, prior_snapshot)
        else:
            discarded_tools = []
            for dm in discarded_messages:
                if dm.get("tool_calls"):
                    discarded_tools.extend(dm["tool_calls"])
            if discarded_tools:
                from core.character import rollback_tool_effects
                rollback_tool_effects(target_save_id, discarded_tools)

        # Truncate history to the point right before this assistant turn started
        self.save_history[target_save_id] = history[:turn_start_idx]
        self._save_to_disk(target_save_id)

        res = await self.run_async(
            save_id=target_save_id,
            new_message_text=None,
            model=model,
            speaker_id=speaker_id,
        )

        # Restore subsequent messages in place if any
        if subsequent_messages:
            self.save_history[target_save_id].extend(subsequent_messages)
            self._save_to_disk(target_save_id)

        return res

    async def reset_save(self, save_id: str):
        target_save_id = self._normalize_save_id(save_id)
        with self._lock:
            self.save_history.pop(target_save_id, None)
            self.save_memory_state.pop(target_save_id, None)

            try:
                from core.save_manager import create_fresh_save_bundle, write_save
                fresh_bundle = create_fresh_save_bundle(target_save_id)
                write_save(target_save_id, fresh_bundle)
                self._load_from_disk(target_save_id)
            except Exception as e:
                print(f"Error resetting save {target_save_id} to fresh state: {e}")

            try:
                from core.skills.vectorized_databank.databank import DataBankManager
                DataBankManager(save_id=target_save_id).delete_chat_history(target_save_id)
            except Exception as e:
                print(f"Error cleaning up databank history on save reset: {e}")

    async def reset_session(self, session_id: str):
        return await self.reset_save(session_id)

    async def delete_system_memory(self, save_id: str = None, timestamp: float = 0.0, session_id: str = None) -> bool:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            if target_save_id not in self.save_history:
                self._load_from_disk(target_save_id)

            marked_compacted = False
            for msg in self.save_history.get(target_save_id, []):
                if msg.get("role") == "system-memory" and abs(msg.get("timestamp", 0) - timestamp) < 1.0:
                    msg["compacted"] = True
                    marked_compacted = True
                    print("[MEMORY DELETE] Marked OS message as compacted.", flush=True)

            if marked_compacted:
                self._save_to_disk(target_save_id)

            return marked_compacted

    async def delete_turn(self, save_id: str = None, msg_id: str = None, session_id: str = None) -> bool:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            if target_save_id not in self.save_history:
                self._load_from_disk(target_save_id)

            history = self.save_history.get(target_save_id)
            if history is None:
                raise ValueError("Save not found")

            user_idx = next((i for i, ev in enumerate(history) if ev.get("id") == msg_id), -1)
            if user_idx == -1:
                raise ValueError("User message not found")

            next_user_idx = next((i for i in range(user_idx + 1, len(history)) if is_real_user_msg(history[i])), -1)

            self.save_history[target_save_id] = history[:user_idx] + (history[next_user_idx:] if next_user_idx != -1 else [])
            self._save_to_disk(target_save_id)
            return True

    async def delete_message_at(self, save_id: str = None, msg_id: str = None, session_id: str = None) -> bool:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            if target_save_id not in self.save_history:
                self._load_from_disk(target_save_id)

            history = self.save_history.get(target_save_id, [])
            for i, msg in enumerate(history):
                if msg.get("id") == msg_id:
                    if msg.get("tool_calls"):
                        from core.character import rollback_tool_effects
                        rollback_tool_effects(target_save_id, msg["tool_calls"])
                    del history[i]
                    self._save_to_disk(target_save_id)
                    return True
            return False

    async def delete_image_from_save(self, save_id: str = None, image_url: str = None, session_id: str = None) -> bool:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            if target_save_id not in self.save_history:
                self._load_from_disk(target_save_id)

            history = self.save_history.get(target_save_id)
            if history is None:
                return self._delete_local_image(image_url)

            modified = False
            indices_to_delete = set()
            base_url = image_url.split("?")[0]
            pattern = r"!\[[^\]]*\]\(" + re.escape(base_url) + r"(?:\?[^)]*)?\)"

            for i, msg in enumerate(history):
                has_image = False

                if msg.get("text") and base_url in msg["text"]:
                    has_image = True
                    remaining_text = re.sub(pattern, "", msg["text"]).strip()
                    if not re.sub(r"^[:\s\-\*]+|[:\s\-\*]+$", "", remaining_text):
                        indices_to_delete.add(i)
                    else:
                        msg["text"] = remaining_text
                    modified = True

                if msg.get("image_url") and base_url in msg["image_url"]:
                    has_image = True
                    msg["image_url"] = None
                    if not (msg.get("text") or "").strip():
                        indices_to_delete.add(i)
                    modified = True

                if tool_calls := msg.get("tool_calls"):
                    cleared_call_ids = set()
                    for tc in tool_calls:
                        if tc.get("type") == "response" and tc.get("response") and base_url in tc["response"]:
                            has_image = True
                            tc["response"] = re.sub(pattern, "", tc["response"]).strip()
                            if not tc["response"]:
                                cleared_call_ids.add(tc.get("id"))
                            modified = True

                    if cleared_call_ids:
                        msg["tool_calls"] = [
                            tc
                            for tc in tool_calls
                            if not (
                                tc.get("id") in cleared_call_ids
                                and (tc.get("type") == "call" or not (tc.get("response") or "").strip())
                            )
                        ]

                    if not any(tc.get("response", "").strip() for tc in msg["tool_calls"] if tc.get("type") == "response"):
                        if not (msg.get("text") or "").strip():
                            indices_to_delete.add(i)

                if has_image and i > 0:
                    prev_msg = history[i - 1]
                    if prev_msg.get("role") == "user" and any(k in (prev_msg.get("text") or "") for k in ("Generate a portrait of yourself", "[GENERATE_IMAGE:", "[GENERATE_IMAGEN:")):
                        indices_to_delete.add(i - 1)

            for idx in sorted(indices_to_delete, reverse=True):
                if 0 <= idx < len(history):
                    del history[idx]
                    modified = True

            file_deleted = self._delete_local_image(image_url)
            if modified:
                self._save_to_disk(target_save_id)

            return modified or file_deleted

    async def delete_image_from_session(self, session_id: str, image_url: str) -> bool:
        return await self.delete_image_from_save(save_id=session_id, image_url=image_url)

    async def replace_image_in_save(
        self, save_id: str = None, old_image_url: str = None, new_image_url: str = None, new_prompt: str = None, session_id: str = None
    ) -> bool:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            if target_save_id not in self.save_history:
                self._load_from_disk(target_save_id)

            history = self.save_history.get(target_save_id)
            if history is None:
                return False

            modified = False
            for msg in history:
                if msg.get("text") and old_image_url in msg["text"]:
                    msg["text"] = msg["text"].replace(old_image_url, new_image_url)
                    modified = True

                if msg.get("image_url") == old_image_url:
                    msg["image_url"] = new_image_url
                    modified = True

                if tool_calls := msg.get("tool_calls"):
                    call_ids_to_update = set()
                    for tc in tool_calls:
                        if tc.get("type") == "response" and tc.get("response") and old_image_url in tc["response"]:
                            tc["response"] = tc["response"].replace(old_image_url, new_image_url)
                            modified = True
                            if tc.get("id"):
                                call_ids_to_update.add(tc["id"])

                    if new_prompt and call_ids_to_update:
                        for tc in tool_calls:
                            if tc.get("type") == "call" and tc.get("id") in call_ids_to_update and isinstance(tc.get("args"), dict):
                                tc["args"]["prompt"] = new_prompt
                                modified = True

            if modified:
                self._save_to_disk(target_save_id)

            return modified

    async def replace_image_in_session(
        self, session_id: str, old_image_url: str, new_image_url: str, new_prompt: str = None
    ) -> bool:
        return await self.replace_image_in_save(save_id=session_id, old_image_url=old_image_url, new_image_url=new_image_url, new_prompt=new_prompt)

    async def replace_image_with_video_in_save(self, save_id: str = None, old_image_url: str = None, new_video_url: str = None, session_id: str = None) -> bool:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            if target_save_id not in self.save_history:
                self._load_from_disk(target_save_id)
            if target_save_id not in self.save_history:
                return False
                
            history = self.save_history[target_save_id]
            modified = False
            
            for msg in history:
                if msg.get('text') and old_image_url in msg['text']:
                    msg['text'] = msg['text'].replace(old_image_url, new_video_url)
                    modified = True
                if msg.get('image_url') == old_image_url:
                    msg['image_url'] = new_video_url
                    modified = True
                if msg.get('tool_calls'):
                    for tc in msg['tool_calls']:
                        if tc.get('type') == 'response' and tc.get('response') and old_image_url in tc['response']:
                            tc['response'] = tc['response'].replace(old_image_url, new_video_url)
                            modified = True
                            
            if modified:
                self._save_to_disk(target_save_id)
                return True
            return False

    async def replace_image_with_video_in_session(self, session_id: str, old_image_url: str, new_video_url: str) -> bool:
        return await self.replace_image_with_video_in_save(save_id=session_id, old_image_url=old_image_url, new_video_url=new_video_url)

    async def append_message_to_save(
        self,
        save_id: str = None,
        role: str = None,
        text: str = None,
        sender_id: str | None = None,
        sender_name: str | None = None,
        tool_calls: list | None = None,
        session_id: str = None,
    ) -> dict:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            if target_save_id not in self.save_history:
                self._load_from_disk(target_save_id)
            if target_save_id not in self.save_history:
                self.save_history[target_save_id] = []
                
            prefix = 'usr_' if role == 'user' else 'prgm_'
            if role == 'user':
                if text.startswith("[SYSTEM: User has completed"):
                    prefix = "quest_"
                elif "Send me a portrait of yourself" in text or "[GENERATE_IMAGE:" in text or "[GENERATE_IMAGEN:" in text:
                    prefix = "port_"
                elif text.startswith("[Tool Response from"):
                    prefix = "tool_"
                elif text.strip().startswith("![") and text.strip().endswith(")"):
                    prefix = "img_"
            else:
                if text.strip().startswith("![") and text.strip().endswith(")"):
                    prefix = "img_"
            
            from runners.follower import get_active_follower
            from core.follower_config import get_follower_name
            from core.world_engine import load_world_state
            world = load_world_state(target_save_id)
            t_date = world.get("date") or world.get("tamrielic_date") or {"day": 1, "month": "Hearthfire", "year": 389, "hour": 6}

            if role != 'user':
                resolved_sender_id = sender_id or get_active_follower()
                resolved_sender_name = sender_name or get_follower_name(resolved_sender_id) or "Follower"
            else:
                resolved_sender_id = sender_id
                resolved_sender_name = sender_name

            history = self.save_history[target_save_id]
            new_msg = {
                'id': f"{prefix}{uuid.uuid4().hex}",
                'role': 'user' if role == 'user' else 'follower',
                'text': text,
                'tool_calls': tool_calls or [],
                'tamrielic_date': t_date,
                'timestamp': time.time()
            }
            if resolved_sender_id:
                new_msg['sender_id'] = resolved_sender_id
                new_msg['sender_name'] = resolved_sender_name

            history.append(new_msg)
            self._save_to_disk(target_save_id)
            return new_msg

    async def append_message_to_session(
        self,
        session_id: str,
        role: str,
        text: str,
        sender_id: str | None = None,
        sender_name: str | None = None,
        tool_calls: list | None = None,
    ) -> dict:
        return await self.append_message_to_save(
            save_id=session_id,
            role=role,
            text=text,
            sender_id=sender_id,
            sender_name=sender_name,
            tool_calls=tool_calls,
        )

    async def update_message_text(self, save_id: str = None, msg_id: str = None, new_text: str = None, session_id: str = None) -> bool:
        target_save_id = self._normalize_save_id(save_id or session_id)
        with self._lock:
            if target_save_id not in self.save_history:
                self._load_from_disk(target_save_id)
            if target_save_id not in self.save_history:
                return False
                
            real_history = self.save_history[target_save_id]
            found_idx = -1
            for i, msg in enumerate(real_history):
                if msg.get('id') == msg_id:
                    found_idx = i
                    break
                    
            if found_idx != -1:
                target_msg = real_history[found_idx]
                if '<!-- check:' in target_msg.get('text', ''):
                    return False
                target_msg['text'] = new_text
                role = target_msg.get('role')
                if role in ('follower', 'model'):
                    prev_user_idx = -1
                    for k in range(found_idx - 1, -1, -1):
                        if is_real_user_msg(real_history[k]):
                            prev_user_idx = k
                            break
                    next_user_idx = len(real_history)
                    for k in range(found_idx + 1, len(real_history)):
                        if is_real_user_msg(real_history[k]):
                            next_user_idx = k
                            break
                            
                    for k in range(prev_user_idx + 1, next_user_idx):
                        if k != found_idx:
                            m = real_history[k]
                            if m.get('role') in ('follower', 'model'):
                                m['text'] = ""
                                
                self._save_to_disk(target_save_id)
                return True
            return False