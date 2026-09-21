import asyncio
import base64
import json
import mimetypes
import os
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import tools.tools as tools
from utils.utils import (
    _merge_consecutive_messages,
    _ARENA_DIRECTIVE_PROMPT
)


def _get_base64_image_url(image_source: str | None) -> str | None:
    """Resolves an image file path or URL into a base64 data URL."""
    if not image_source:
        return None

    src_str = str(image_source)
    if src_str.startswith("data:"):
        return src_str

    project_root = Path(__file__).resolve().parent.parent

    if src_str.startswith("/images/"):
        rel_path = src_str.removeprefix("/images/")
        from runners.follower import get_active_follower
        active_follower = get_active_follower()
        local_path = project_root / "core" / "followers" / active_follower / rel_path
    else:
        local_path = Path(src_str)
        if not local_path.is_absolute():
            local_path = project_root / local_path

    local_path = local_path.resolve()

    if not local_path.is_file():
        print(f"[IMAGE RESOLVE] File not found: {local_path}")
        return None

    try:
        mime_type, _ = mimetypes.guess_type(local_path)
        mime_type = mime_type or "image/png"
        b64_data = base64.b64encode(local_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{b64_data}"
    except Exception as e:
        print(f"[IMAGE RESOLVE ERROR] Failed to encode {local_path}: {e}")
        return None


class LocalHistoryAdapter(ABC):
    def __init__(self, runner_obj, session_id: str):
        self.runner_obj = runner_obj
        self.session_id = session_id

    @abstractmethod
    def get_openai_messages(self, sys_inst: str, rag_context: str, memory_context: str | None = None, response_only: bool = False, speaker_id: str = "game") -> list[dict]:
        pass

    @abstractmethod
    def append_assistant_message(self, text: str, tool_calls_data: list, invocation_id: str, intermediate: bool = False, speaker_id: str = "game", speaker_name: str | None = None):
        pass

    @abstractmethod
    def append_tool_events(self, results: list, invocation_id: str):
        pass

    @abstractmethod
    def append_image_tool_events(self, tool_name: str, tool_args: dict, new_markdown: str, call_id: str, invocation_id: str):
        pass

    @abstractmethod
    def post_process_thoughts(self, invocation_id: str):
        pass

    @abstractmethod
    def save(self):
        pass

    async def compact_history(self, active_model: str, force: bool = False):
        """Optional hook for history compaction."""
        pass


class OsHistoryAdapter(LocalHistoryAdapter):
    def __init__(self, runner_obj, session_id: str, file_path_resolved, image_data, image_mime, query_vector=None):
        super().__init__(runner_obj, session_id)
        self.file_path_resolved = file_path_resolved
        self.image_data = image_data
        self.image_mime = image_mime
        self.query_vector = query_vector
        self.initial_history_len = len(runner_obj.sessions_history.get(session_id, []))
        self._calculate_context_threshold()

    def _calculate_context_threshold(self):
        """Derives local character threshold limit from environment configuration."""
        local_context = os.getenv("LOCAL_CONTEXT")
        if local_context and local_context.isdigit():
            self.max_context_chars = int(int(local_context) * 0.30 * 4)
        else:
            self.max_context_chars = int(os.getenv("LOCAL_CONTEXT_THRESHOLD_CHARS", "6000"))

    async def compact_history(self, active_model: str, force: bool = False):
        """Compacts older history turns into vectorized memory chunks."""
        history = self.runner_obj.sessions_history.get(self.session_id, [])
        uncompacted_length = sum(len(msg.get("text") or "") for msg in history if not msg.get("compacted"))

        if not force and uncompacted_length <= self.max_context_chars:
            return

        user_msg_indices = [idx for idx, msg in enumerate(history) if msg.get("role") == "user" and not msg.get("compacted")]
        keep_turns = 2 if force else 4

        if len(user_msg_indices) <= keep_turns:
            return

        cutoff_idx = user_msg_indices[-keep_turns]
        historical_turns = history[:cutoff_idx]
        uncompacted_turns = [msg for msg in historical_turns if not msg.get("compacted")]

        summary_lines = [
            f"{'User' if msg.get('role') == 'user' else 'Follower'}: {msg.get('text', '').strip()}"
            for msg in uncompacted_turns
            if msg.get("role") in ("user", "follower") and msg.get("text", "").strip()
        ]

        text_to_summarize = "\n".join(summary_lines)
        if not text_to_summarize:
            return

        from core.skills.vectorized_databank.databank import DataBankManager
        prior_texts = []
        try:
            db = DataBankManager()
            priors = db.get_prior_chat_histories(self.session_id, limit=2)
            prior_texts = [f"--- PRIOR MEMORY ARCHIVE ({p['name']}) ---\n{p['text']}" for p in priors]
        except Exception as e:
            print(f"[COMPACTION OS] Error fetching prior chat histories: {e}", flush=True)

        summary = await self.runner_obj._generate_local_summary(text_to_summarize, active_model, prior_memories=prior_texts)
        if summary.startswith("Memory compaction summary generation failed"):
            summary = (
                "Older conversation turns were pruned to free up local memory. "
                "The full transcript of these turns has been archived in the vector database."
            )

        try:
            db = DataBankManager()
            db.ingest_text(
                text=summary,
                name=f"chat_history_archive_{self.session_id}_{int(time.time())}",
                source_type="chat_history",
            )
            db.prune_chat_histories(self.session_id, keep_limit=3)

            priors = db.get_prior_chat_histories(self.session_id, limit=3)
            if len(priors) == 3 and len(priors[-1].get("text", "")) > 1200:
                asyncio.create_task(self._background_distill(priors[-1], active_model, db))
        except Exception as e:
            print(f"[COMPACTION OS ERROR] Failed to ingest: {e}", flush=True)

        summary_msg = {
            "id": f"sys_{uuid.uuid4().hex}",
            "role": "system-memory",
            "text": f"[System Memory of older conversation turns]:\n{summary}",
            "timestamp": time.time(),
        }

        with self.runner_obj._lock:
            live_history = self.runner_obj.sessions_history.get(self.session_id, [])
            last_id = historical_turns[-1].get("id") if historical_turns else None

            if last_id:
                idx = next((i for i, msg in enumerate(live_history) if msg.get("id") == last_id), -1)
                if idx != -1:
                    for msg in live_history[: idx + 1]:
                        msg["compacted"] = True
                    live_history.insert(idx + 1, summary_msg)

            self.runner_obj._save_session_to_disk(self.session_id)

    async def _background_distill(self, oldest_doc: dict, active_model: str, db):
        try:
            chronicle = await self.runner_obj._distill_epic_chronicle(oldest_doc["text"], active_model)
            if chronicle and not chronicle.startswith("Distillation failed"):
                db.update_memory_document(oldest_doc["name"], chronicle)
        except Exception as e:
            print(f"[COMPACTION OS ERROR] Background distillation failed: {e}", flush=True)

    def _build_tiered_messages(
        self,
        core_system_content: str = "",
        raw_messages: list[dict] = None,
        post_injection: str = "",
        auxiliary_context: list[str] | None = None,
        max_input_tokens: int = 6500,
        system_content: str = None,
    ) -> list[dict]:
        """
        Assembles OpenAI payload with clean separation:
          - System message: Combines core directives, world state/character context, and active lore/auxiliary knowledge.
          - Chat history: Pure conversation turns between user and assistant, trimmed from newest to oldest within character budget.
          No world info, lore, or state tags are ever appended to user or assistant messages.
        """
        core_system = (core_system_content or system_content or "").strip()
        raw_messages = list(raw_messages or [])
        auxiliary_context = auxiliary_context or []
        CHAR_BUDGET = max_input_tokens * 4

        # 1. Build System Context
        system_blocks = [core_system]
        if post_injection:
            system_blocks.append(post_injection.strip())

        # Fit auxiliary context into available system budget
        accumulated_system_len = sum(len(b) for b in system_blocks)
        included_aux = []
        for block in auxiliary_context:
            block_str = str(block).strip()
            if not block_str:
                continue
            if accumulated_system_len + len(block_str) + 2 <= (CHAR_BUDGET // 2):
                included_aux.append(block_str)
                accumulated_system_len += len(block_str) + 2

        if included_aux:
            system_blocks.append("\n\n".join(included_aux))

        full_system = "\n\n".join(b for b in system_blocks if b)

        # 2. Allocate remaining budget to pure conversation turns (newest to oldest)
        remaining_budget = max(4000, CHAR_BUDGET - len(full_system))
        chat_turns = [m for m in raw_messages if m.get("role") != "system"]

        trimmed_chat_turns = []
        accumulated_chat_chars = 0

        for turn in reversed(chat_turns):
            turn_text = turn["content"] if isinstance(turn["content"], str) else "".join(
                item.get("text", "") for item in turn["content"] if isinstance(item, dict)
            )
            turn_len = len(turn_text)

            if accumulated_chat_chars + turn_len <= remaining_budget:
                trimmed_chat_turns.insert(0, turn)
                accumulated_chat_chars += turn_len
            else:
                break

        final_messages = [{"role": "system", "content": full_system}]
        final_messages.extend(trimmed_chat_turns)

        return _merge_consecutive_messages(final_messages)

    def get_openai_messages(self, sys_inst: str, rag_context: str, memory_context: str | None = None, response_only: bool = False, speaker_id: str = "game") -> list[dict]:
        from core.follower_config import replace_placeholders
        from core.lorebook import get_active_lore
        from runners.follower import get_active_follower
        from variables.settings import FOLLOWERS_DIR

        history = self.runner_obj.sessions_history.get(self.session_id, [])
        filtered_history = [
            msg for msg in history
            if msg.get("role") not in ("voice-call", "system-memory") and not msg.get("compacted")
            and not (msg.get('role') == 'follower' and not (msg.get('text') or '').strip() and not msg.get('tool_calls') and not msg.get('id', '').startswith('first_mes'))
        ]

        if response_only:
            latest_user = next(
                (
                    msg for msg in reversed(filtered_history)
                    if msg.get('role') == 'user'
                    and not msg.get('id', '').startswith('tool_')
                    and not msg.get('text', '').startswith('[Tool Response from')
                ),
                None
            )
            filtered_history = [latest_user] if latest_user else []

        if not filtered_history:
            return [{"role": "system", "content": sys_inst}]

        latest_img_idx = -1
        has_new_image = bool((self.image_data and self.image_mime) or self.file_path_resolved)

        for idx in range(len(filtered_history) - 1, -1, -1):
            msg = filtered_history[idx]
            if msg.get("role") == "user":
                if msg.get("id", "").startswith("tool_") or msg.get("text", "").startswith("[Tool Response from"):
                    continue
                if has_new_image or msg.get("image_url"):
                    latest_img_idx = idx
                break

        active_speaker = speaker_id or "game"
        raw_messages = []
        for idx, msg in enumerate(filtered_history):
            msg_role = msg.get("role")
            
            if msg.get('id', '').startswith('first_mes'):
                from core.follower_config import get_follower_greeting
                raw_text = get_follower_greeting("game")
                msg_sender = "game"
            else:
                raw_text = msg.get('text', '') or msg.get('content', '') or ''
                msg_sender = msg.get("sender_id") or ("game" if msg_role == "follower" else None)
                
            content_text = replace_placeholders(raw_text)

            if msg_role == "user":
                role = "user"
                if not content_text.startswith(("[Tool Response", "[SYSTEM:")):
                    from runners.follower import get_player_name
                    player_name = get_player_name()
                    if player_name and not content_text.startswith(f"[{player_name}") and not content_text.startswith(f"{player_name}:"):
                        content_text = f"[{player_name} (Hero)]: {content_text}"
            else:
                # Character message in history: assistant if active speaker, else user
                if msg_sender == active_speaker:
                    role = "assistant"
                else:
                    role = "user"
                    sender_name = msg.get("sender_name")
                    if not sender_name:
                        if msg_sender == "game":
                            sender_name = "The Game"
                        else:
                            from core.follower_config import get_follower_name
                            sender_name = get_follower_name(msg_sender)
                    role_label = "Referee" if msg_sender == "game" else "Follower"
                    tag = f"[{sender_name} ({role_label})]"
                    if sender_name and not content_text.startswith(f"[{sender_name}") and not content_text.startswith(f"{sender_name}:"):
                        content_text = f"{tag}: {content_text}"

            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("type") == "call":
                        args_list = [
                            f'{k}="{v.replace('"', '\\"')}"' if isinstance(v, str) else f"{k}={v}"
                            for k, v in tc.get("args", {}).items()
                        ]
                        content_text += f"\n[{tc.get('name')}({', '.join(args_list)})]"

            if idx == latest_img_idx:
                img_src = (
                    f"data:{self.image_mime};base64,{self.image_data}"
                    if self.image_data and self.image_mime
                    else self.file_path_resolved or msg.get("image_url")
                )
                b64_url = _get_base64_image_url(img_src)
                if b64_url:
                    raw_messages.append({
                        "role": role,
                        "content": [
                            {"type": "text", "text": content_text},
                            {"type": "image_url", "image_url": {"url": b64_url}},
                        ],
                    })
                    continue

            if msg.get("image_url"):
                content_text = f"{content_text} (image: [Attached Image])".strip()
            raw_messages.append({"role": role, "content": content_text})

        # Base System instructions and Directives (Tier 1 Core)
        core_system = sys_inst
            
        try:
            from core.banned_words import get_banned_words_directive
            banned_dir = get_banned_words_directive()
            if banned_dir:
                core_system += f"\n\n{banned_dir}"
        except Exception:
            pass

        # Image generation system override (Tier 1 Core)
        last_user_msg = next(
            (
                m.get("text", "") for m in reversed(filtered_history)
                if m.get("role") == "user"
                and not m.get("id", "").startswith("tool_")
                and not m.get("text", "").startswith("[Tool Response from")
            ),
            "",
        )

        is_image_request = (
            "[GENERATE_IMAGE" in (last_user_msg or "")
            or "Send me a portrait of yourself" in (last_user_msg or "")
            or (last_user_msg or "").startswith("[Render image")
        )
        if is_image_request:
            core_system += (
                "\n\n[CRITICAL IMAGE DIRECTIVE: The user requested an image of the active follower. "
                "You must ONLY output the image generation tool call tag: `[generate_local_image(prompt=\"...\")]` "
                "or `[generate_imagen(prompt=\"...\")]` depicting an image of the active follower character. "
                "Do NOT write any story narrative or dialogue. "
                "Do NOT advance the plot. "
                "Do NOT call any gameplay mechanics tools or add/remove items. "
                "Output ONLY the image tool call tag.]"
            )

        # Tier 3 & 4 Auxiliary Blocks (Lore, Memory, Journals, RAG, Skills)
        auxiliary_blocks = []
        active_fol = get_active_follower()

        # Lore Injection
        try:
            lore_before, lore_after = get_active_lore(active_fol, filtered_history)
            all_lore = [entry.strip() for entry in (lore_before + lore_after) if entry and entry.strip()]
            if all_lore:
                auxiliary_blocks.append(f"# WORLD LORE & SETTING BACKGROUND\n" + "\n\n".join(all_lore))
        except Exception as le:
            print(f"[lorebook] Injection error: {le}")

        # System Memory
        for msg in history:
            if msg.get("role") == "system-memory" and msg.get("text", "").strip():
                clean_mem = msg["text"].replace("[System Memory of older conversation turns]:", "").strip()
                auxiliary_blocks.append(f"# CONVERSATION MEMORY\n{replace_placeholders(clean_mem)}")

        # Journals
        if last_user_msg and not response_only:
            try:
                from core.journals import match_journals
                matched = match_journals(last_user_msg, active_fol)
                if matched:
                    journals_text = "\n".join(f"- {replace_placeholders(e['content'])}" for e in matched)
                    auxiliary_blocks.append(f"# RECALLED JOURNALS\n{journals_text}")
            except Exception as je:
                print(f"Error matching journals: {je}")

        # Knowledge Base & Archived Memory
        if rag_context:
            auxiliary_blocks.append(f"# KNOWLEDGE BASE\n{rag_context}")
        if memory_context and not response_only:
            auxiliary_blocks.append(f"# ARCHIVED MEMORY\n{replace_placeholders(memory_context)}")

        # Skills (On-demand trigger retrieval)
        if last_user_msg and not response_only:
            try:
                from core.skill_retriever import retrieve_skill_instructions
                skills = retrieve_skill_instructions(
                    query=last_user_msg,
                    threshold=0.35,
                    top_k=2,
                )
                if skills:
                    auxiliary_blocks.append(skills)
            except Exception as se:
                print(f"[skills] Retrieval error: {se}")

        # Gather Post-History System Context (Character Sheet, World Engine State & Quests)
        full_post_injection = ""
        try:
            from runners.follower import get_active_user
            from core.save_manager import get_active_save_id
            from core.world_engine import load_world_state
            from core.character import load_character, get_character_context

            active_user = get_active_user()
            active_save_id = get_active_save_id()
            sheet = load_character(active_save_id)
            char_ctx = get_character_context(sheet) if sheet else ""

            world = load_world_state(active_user)
            t_date = world.get("date") or world.get("tamrielic_date") or {"day": 1, "month": "Hearthfire", "year": 389, "hour": 6}
            hour = t_date.get("hour", 6)
            
            disp_hour = hour % 12 or 12
            am_pm = "AM" if hour < 12 else "PM"
            time_display = f"{disp_hour}:00 {am_pm}"
            
            prov = world.get("current_province", "Cyrodiil")
            loc = world.get("current_location", "Imperial Dungeon")
            day = t_date.get("day", 1)
            month = t_date.get("month", "Hearthfire")
            year = t_date.get("year", 389)
            
            state_tag = f'<!-- state: province="{prov}", location="{loc}", date="{day} {month}, 3E {year}", hour={hour}, time="{time_display}" -->'
            
            post_blocks = []
            if char_ctx:
                post_blocks.append(f"# PLAYER CHARACTER\n{char_ctx}")
                
            try:
                from core.quest_tracker import load_quest_stages, get_current_stage
                stages = load_quest_stages()
                q_stage_num = world.get("quest_stage", 10)
                current_stage = get_current_stage(q_stage_num, stages)
                if current_stage:
                    post_blocks.append(
                        f"# ACTIVE MAIN QUEST\n"
                        f"- Quest: {current_stage.get('quest_title', 'Main Quest')}\n"
                        f"- Stage: {q_stage_num}\n"
                        f"- Objective: {current_stage.get('objective', '')} (Call [arena_advance_stage] when completed).\n"
                        f"- Next Stage: {current_stage.get('next_stage', 'Complete')}"
                    )
            except Exception as _qe:
                print(f"Error compiling active quest context: {_qe}", flush=True)

            if sheet and sheet.get("derived", {}).get("hp_current", 1) <= 0:
                post_blocks.append(
                    "\n\n[CRITICAL GAME OVER DIRECTIVE: The player character's health has reached 0 (DEAD). "
                    "You MUST narrate the fatal strike and perishing of the hero in visceral detail. "
                    "Declare a definitive GAME OVER state. "
                    "Do NOT allow the player to survive, take further actions, or recover. "
                    "Conclude the narrative with their tragic perishing in Tamriel.]"
                )
            post_blocks.append(f"# CURRENT WORLD STATE\n- Province: {prov}\n- Location: {loc}\n- Date: {day} {month}, 3E {year}\n- Time: {time_display}\n{state_tag}")
            full_post_injection = "\n\n".join(post_blocks)

        except Exception as e:
            print(f"Error compiling unified player status / world state in post history: {e}", flush=True)

        # Build final array adhering to tiered budget limits
        return self._build_tiered_messages(
            core_system_content=core_system,
            raw_messages=raw_messages,
            post_injection=full_post_injection,
            auxiliary_context=auxiliary_blocks,
            max_input_tokens=6500
        )

    def append_assistant_message(self, text: str, tool_calls_data: list, invocation_id: str, intermediate: bool = False, speaker_id: str = "game", speaker_name: str | None = None):
        from runners.follower import get_active_user
        from core.world_engine import (
            load_world_state,
            create_state_snapshot,
            apply_state_snapshot,
            extract_hidden_state_footer
        )
        from core.character import load_character

        active_user = get_active_user()
        world_state = load_world_state(active_user)
        character_sheet = load_character(active_user)
        current_snapshot = create_state_snapshot(world_state, character_sheet)

        cleaned_text, updated_snapshot = extract_hidden_state_footer(text, current_snapshot)
        apply_state_snapshot(active_user, updated_snapshot)

        t_date = (updated_snapshot.get("date") if updated_snapshot else None) or world_state.get("date") or world_state.get("tamrielic_date") or {"day": 1, "month": "Hearthfire", "year": 389, "hour": 6}

        history = self.runner_obj.sessions_history[self.session_id]

        sender_id = speaker_id or "game"
        sender_name = speaker_name
        if not sender_name:
            if sender_id == "game":
                sender_name = "The Game"
            else:
                from core.follower_config import get_follower_name
                sender_name = get_follower_name(sender_id)

        follower_id = sender_id if sender_id not in ("game", "user") else None
        if history and history[-1]["role"] == "follower" and history[-1].get("sender_id", "game") == sender_id:
            history[-1].update({
                "text": cleaned_text,
                "tool_calls": tool_calls_data,
                "tamrielic_date": t_date,
                "sender_id": sender_id,
                "follower_id": follower_id,
                "sender_name": sender_name,
            })
            history[-1].pop('state_snapshot', None)
            return history[-1]

        if intermediate:
            msg_prefix = f"itm_{sender_id}_"
        elif cleaned_text and cleaned_text.strip().startswith("![") and cleaned_text.strip().endswith(")"):
            msg_prefix = f"img_{sender_id}_"
        elif sender_id == "game":
            msg_prefix = "game_"
        else:
            msg_prefix = f"fol_{sender_id}_"

        bot_msg = {
            "id": f"{msg_prefix}{uuid.uuid4().hex[:10]}",
            "role": "follower",
            "text": cleaned_text,
            "tool_calls": tool_calls_data,
            "tamrielic_date": t_date,
            "timestamp": time.time(),
            "sender_id": sender_id,
            "follower_id": follower_id,
            "sender_name": sender_name,
        }
        history.append(bot_msg)
        return bot_msg

    def append_tool_events(self, results: list, invocation_id: str):
        for t_name, _, t_output in results:
            self.runner_obj.sessions_history[self.session_id].append({
                "id": f"tool_{uuid.uuid4().hex}",
                "role": "user",
                "text": f"[Tool Response from {t_name}]:\n{t_output}",
                "tool_calls": [],
                "timestamp": time.time(),
            })

    def append_image_tool_events(self, tool_name: str, tool_args: dict, new_markdown: str, call_id: str, invocation_id: str):
        pass

    def post_process_thoughts(self, invocation_id: str):
        pass

    def save(self):
        self.runner_obj._save_session_to_disk(self.session_id)