import ast
import asyncio
import base64
import copy
import httpx
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path

import tools.tools as tools
from variables.settings import FOLLOWERS_DIR, LOCAL_SERVER_URL, get_local_server_headers
from models.models import is_local_model
from runners.follower import get_active_follower

# Constants
VECTOR_QUERY_MESSAGES = 3
VECTOR_TOP_K = 7
VECTOR_SCORE_THRESHOLD = 0.25
VECTOR_TOKEN_BUDGET = 2048

def atomic_save_json(path: str | Path, data: object, indent: int = 2):
    """Atomically writes JSON to disk using a unique temporary file and replacement."""
    target_path = str(path)
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    temp_path = f"{target_path}.tmp_{uuid.uuid4().hex[:6]}"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    os.replace(temp_path, target_path)


_ARENA_DIRECTIVE_PROMPT = (
    "\n\n# ARENA RPG DIRECTIVES\n"
    "Tools:\n"
    "- `[arena_request_skill_check(skill_name=\"...\", attribute_name=\"...\", dc=..., reason=\"...\")]` Trigger player D20 check.\n"
    "- `[arena_spend_magicka(amount=...)]` Deduct spell MP cost.\n"
    "- `[arena_spend_stamina(amount=...)]` Deduct exertion Stamina.\n"
    "- `[arena_take_damage(amount=...)]` Deduct injury HP.\n"
    "- `[arena_heal(amount=...)]` Restore HP.\n"
    "- `[arena_roll_combat(attacker_name=\"...\", attacker_strength=..., attacker_agility=..., attacker_class_archetype=\"...\", weapon_name=\"...\", weapon_damage_tier=..., weapon_attribute=\"...\", target_name=\"...\", target_agility=...)]` NPC/monster attack.\n"
    "- `[arena_roll_check(attribute_name=\"...\", attribute_value=..., dc=...)]` NPC/monster check.\n"
    "- `[arena_recruit_follower(follower_name=\"...\", follower_race=\"...\", follower_class=\"...\", persona_description=\"...\")]` Recruit permanent companion.\n"
    "- `[generate_local_image(prompt=\"...\")]` Generate visual art via ComfyUI.\n"
    "- `[arena_add_item(character_name=\"{{user}}\", item_name=\"...\", item_type=\"...\", quantity=1)]` / `[arena_remove_item(...)]` Inventory changes.\n"
    "- `[arena_add_gold(character_name=\"{{user}}\", amount=...)]` / `[arena_spend_gold(...)]` Currency changes.\n\n"
    "Rules:\n"
    "- FORMATTING (MANDATORY): Wrap ALL narration, atmospheric descriptions, environmental details, physical movements, and sensory details in *asterisks* (e.g. *The wall is slick with moisture, and the ledge sits high above.*). Spoken dialogue MUST be in plain text without quotation marks and without asterisks (e.g. Watch your step, {{user}}.). Never output unformatted narration.\n"
    "- SKILL CHECKS: Describe the attempt in *asterisks*, call [arena_request_skill_check], and stop at the moment of action. Await the player's roll. Narrate success or failure only in the subsequent response.\n"
    "- NPC ROLLS: Resolve NPC and creature actions instantly with [arena_roll_combat] or [arena_roll_check].\n"
    "- VITALS: Deduct MP for magic, Stamina for physical exertion, and HP for wounds alongside narrative action.\n"
    "- INVENTORY: Track all item and gold transactions precisely, with the [arena_inventory] skill.\n"
    "- STATE: Resolve environment shifts with <!-- state: province=\"...\", location=\"...\", hours=... --> when location or time changes. Quest progression is handled strictly via [arena_advance_stage].\n"
    "- NARRATION: Use gritty, kinetic prose with anthropological weight. Do not pose questions or choices to {{user}}.\n"
    "- LORE & NAMING: Adhere strictly to canonical Elder Scrolls lore and nomenclature.\n"
)


TOOL_ALIASES = {
    "generate_follower_portrait": "generate_follower_portrait",
    "generate_player_portrait": "generate_player_portrait",
    "generate_environment_image": "generate_environment_image",
    "dalle.text2im": "generate_local_image",
    "dalle:text2im": "generate_local_image",
    "text2im": "generate_local_image",
    "generate_general_image": "generate_imagen",
}

cancelled_sessions = set()
voice_call_sessions = set()

THINK_TAG_PATTERN = re.compile(
    r'(?:<think>|\[think\]|<thought>|\[thought\]|<\|thought\|>|<\|channel\|>thought|<channel\|>thought)'
    r'([\s\S]*?)'
    r'(?:</think>|\[/think\]|</thought>|\[/thought\]|<\|/thought\|>|<\|channel\|>|<channel\|>|<\/\s*think>|\[\s*/\s*think\s*\]|$)',
    re.IGNORECASE
)


def _run_async_in_background_thread(coro):
    def target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        except Exception as e:
            print(f"[BACKGROUND TASK ERROR] {e}", flush=True)
        finally:
            loop.close()

    threading.Thread(target=target, daemon=True).start()


def _is_remote_configured() -> bool:
    """Checks if valid remote cloud configuration environment variables are present."""
    key = os.getenv("REMOTE_API_KEY", "").strip()
    url = os.getenv("REMOTE_CLOUD_URL", "").strip()
    return bool(key and url)


def _merge_consecutive_messages(messages: list[dict]) -> list[dict]:
    """Combines consecutive messages with the same role into a single message."""
    if not messages:
        return []

    merged = []
    for msg in messages:
        if merged and merged[-1]["role"] == msg["role"]:
            prev, curr = merged[-1]["content"], msg["content"]
            if isinstance(prev, str) and isinstance(curr, str):
                merged[-1]["content"] = f"{prev}\n\n{curr}"
            else:
                p_list = prev if isinstance(prev, list) else [{"type": "text", "text": prev}]
                c_list = curr if isinstance(curr, list) else [{"type": "text", "text": curr}]
                merged[-1]["content"] = p_list + c_list
        else:
            merged.append(msg)
    return merged


def _build_vector_query(history: list[dict], max_messages: int = VECTOR_QUERY_MESSAGES) -> str:
    """Constructs a vector search query from the last N non-system conversation messages."""
    valid_roles = {"user", "program", "assistant"}
    messages = []

    for msg in reversed(history):
        if msg.get("role") not in valid_roles:
            continue
        text = msg.get("text", "").strip()
        if not text or text.startswith(("[Tool Response", "[SYSTEM:")):
            continue
        messages.append(text)
        if len(messages) >= max_messages:
            break

    return " ".join(reversed(messages))


def _get_databank_contexts(query_text: str) -> tuple[str, object]:
    """Retrieve knowledge and databank files using vector embeddings."""
    if not query_text:
        return "", None

    try:
        from core.skills.vectorized_databank.databank import DataBankManager, get_embedding_model
        db = DataBankManager()
        if not db._load_data(db.db_path).get("chunks"):
            return "", None

        query_vector = get_embedding_model().encode(query_text)
        rag_context = db.query(
            query_text,
            top_k=VECTOR_TOP_K,
            score_threshold=VECTOR_SCORE_THRESHOLD,
            exclude_source_type="chat_history",
            token_budget=VECTOR_TOKEN_BUDGET,
            query_vector=query_vector,
        )
        return rag_context, query_vector
    except Exception as e:
        print(f"Error querying data bank contexts: {e}")
        return "", None


def _build_tool_calls_pair(tool_name: str, args: dict, output: str, idx: int | None = None) -> list[dict]:
    """Builds a pair of execution call/response dictionaries for tool logging."""
    suffix = f"_{idx}_{uuid.uuid4().hex[:4]}" if idx is not None else ""
    call_id = f"call_{int(time.time())}{suffix}"

    return [
        {"type": "call", "name": tool_name, "args": args, "id": call_id},
        {"type": "response", "name": tool_name, "response": str(output), "id": call_id},
    ]


def _normalize_tool_name(tool_name: str) -> str:
    """Normalizes tool name aliases to standard internal forms."""
    return TOOL_ALIASES.get(tool_name, tool_name)


def _parse_emulated_tool_call(tool_name: str, args_str: str) -> dict:
    """Parses tool call argument strings safely into dictionary structures, 
    handling multi-line code blocks and parameter aliases.
    """
    kwargs = {}
    args = []

    try:
        # Try standard AST parse first
        parsed = ast.parse(f"dummy({args_str})")
        call_node = parsed.body[0].value
        kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in call_node.keywords}
        args = [ast.literal_eval(arg) for arg in call_node.args]
    except Exception:
        # Backup for multi-line / complex arguments (like code blocks)
        # Matches key="value" or key="""value"""
        pattern = re.compile(r'(\w+)\s*=\s*(?:("""|\'\'\'|["\']))([\s\S]*?)\2', re.DOTALL)
        matches = pattern.findall(args_str)
        
        if matches:
            for key, quote, val in matches:
                kwargs[key] = val
        else:
            # Backup for single raw string argument
            val = args_str.strip().strip("'\"")
            if val:
                args = [val]

    # --- Parameter Alias Normalization ---
    if tool_name == "write_file":
        if "filename" in kwargs and "path" not in kwargs:
            kwargs["path"] = kwargs.pop("filename")

    return {"args": args, "kwargs": kwargs}


def _execute_emulated_tool(tool_name: str, args_str: str) -> tuple[dict, str]:
    """Parses and executes an emulated tool call."""
    normalized_name = _normalize_tool_name(tool_name)
    parsed_args = _parse_emulated_tool_call(normalized_name, args_str)

    func = getattr(tools, normalized_name, None)
    if not func:
        return parsed_args, f"Error: Tool '{normalized_name}' not found."

    try:
        output = func(*parsed_args["args"], **parsed_args["kwargs"])
    except Exception as e:
        output = f"Error executing tool: {e}"

    return parsed_args, str(output)


def _get_safe_local_path(image_url: str) -> str | None:
    """Converts an image URL into a safe relative local path for active workspace."""
    if "/images/" not in image_url:
        return None

    raw_path = image_url.split("/images/")[-1].replace("\\", "/")
    safe_parts = [
        "".join(c for c in part if c.isalnum() or c in "._-")
        for part in raw_path.split("/")
        if part
    ]
    
    cleaned_parts = [p for p in safe_parts if p]
    if not cleaned_parts:
        return None

    from runners.follower import get_active_follower
    active_follower = get_active_follower()
    return str(Path("core", "followers", active_follower, *cleaned_parts))


def _get_tool_dedup_keys(norm_name: str, kwargs: dict, pos_args: list = None) -> set:
    keys = set()
    kwargs = kwargs or {}
    pos_args = pos_args or []
    
    primary_val = (
        kwargs.get('skill_name') or
        kwargs.get('attribute_name') or
        kwargs.get('item_name') or
        kwargs.get('item') or
        kwargs.get('target_name') or
        kwargs.get('target') or
        kwargs.get('spell_name') or
        kwargs.get('spell') or
        kwargs.get('effect_name') or
        kwargs.get('condition_name') or
        kwargs.get('amount') or
        (pos_args[0] if pos_args else None)
    )
    
    if primary_val is not None:
        p_str = str(primary_val).strip().lower()
        keys.add((norm_name, p_str))
        
    sorted_str = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    keys.add((norm_name, sorted_str.lower()))
    
    if norm_name in ('arena_request_skill_check', 'request_skill_check'):
        keys.add((norm_name, 'skill_check_generic'))
        
    return keys


def _format_thinking_and_text(thoughts_list: list[str], texts_list: list[str]) -> str:
    """Combines thoughts and texts, normalizing <think> blocks."""
    thoughts_str = "".join(thoughts_list).strip()
    text_str = "".join(texts_list).strip()

    extracted_thoughts = [m.group(1).strip() for m in THINK_TAG_PATTERN.finditer(text_str) if m.group(1).strip()]
    cleaned_text = THINK_TAG_PATTERN.sub("", text_str).strip()

    all_thoughts = [t for t in [thoughts_str] + extracted_thoughts if t]
    combined_thoughts = "\n".join(all_thoughts).strip()

    if combined_thoughts:
        return f"<think> {combined_thoughts}     </think> \n{cleaned_text}"
    return cleaned_text


def strip_story(text: str) -> str:
    """Strips action narration inside asterisks and internal thinking tags."""
    if not text:
        return ""

    text = THINK_TAG_PATTERN.sub('', text)
    text = re.sub(r'<\|channel\|>|<channel\|>', '', text, flags=re.IGNORECASE)

    text = re.sub(r'(?<!\*)\*(?!\*)([\s\S]*?)(?<!\*)\*(?!\*)', '', text)
    text = re.sub(r'(?<!\*)\*(?!\*)', '', text)

    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()


def is_real_user_msg(msg: dict) -> bool:
    """Determine if a message is a real user message."""
    role = msg.get('role')
    msg_id = msg.get('id', '')
    if role != 'user':
        return False
    if msg_id:
        if msg_id.startswith('tool_') or msg_id.startswith('port_') or msg_id.startswith('quest_') or msg_id.startswith('sys_'):
            return False
        if msg_id.startswith('usr_') or msg_id.startswith('img_'):
            return True
    text = msg.get('text', '')
    if text.startswith('[Tool Response') or text.startswith('[SYSTEM:') or "Send me a portrait of yourself" in text:
        return False
    return True


def _convert_json_tool_calls_to_tags(text: str) -> str:
    """Converts standard JSON tool call structures into internal [tool_name(args)] tag formats."""
    if not text or "action" not in text or "action_input" not in text:
        return text

    json_block_pattern = re.compile(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*?\})', re.IGNORECASE)

    def replace_match(match: re.Match) -> str:
        block = match.group(1) or match.group(2)
        try:
            d = json.loads(block)
            act, inp = d.get("action"), d.get("action_input")
            if not act or inp is None:
                return match.group(0)

            norm_act = _normalize_tool_name(act)
            if not hasattr(tools, norm_act) and norm_act not in ("generate_local_image", "generate_imagen"):
                return match.group(0)

            if isinstance(inp, str) and inp.strip().startswith("{"):
                try:
                    inp = json.loads(inp)
                except Exception:
                    pass

            args_list = []
            if isinstance(inp, dict):
                for k, v in inp.items():
                    val_str = f'"{v.replace("\\", "\\\\").replace('"', '\\"')}"' if isinstance(v, str) else str(v)
                    args_list.append(f'{k}={val_str}')
            elif isinstance(inp, str):
                escaped = inp.replace('\\', '\\\\').replace('"', '\\"')
                args_list.append(f'prompt="{escaped}"')

            return f"[{norm_act}({', '.join(args_list)})]"
        except Exception:
            return match.group(0)

    return json_block_pattern.sub(replace_match, text)


def _execute_tool_matches(matches: list, seen_tool_calls: set, session_id: str = None) -> list:
    """Execute ordinary tool tags once and return normalized result tuples."""
    results = []
    for match in matches:
        if session_id and session_id in cancelled_sessions:
            raise asyncio.CancelledError("Session cancelled by user request.")

        tool_name = match.group(1)
        args_string = match.group(2)
        normalized_name = _normalize_tool_name(tool_name)
        parsed_args = _parse_emulated_tool_call(normalized_name, args_string)
        dedup_keys = _get_tool_dedup_keys(
            normalized_name,
            parsed_args["kwargs"],
            parsed_args.get("args", [])
        )

        if any(key in seen_tool_calls for key in dedup_keys):
            output = f"[Skipped: '{normalized_name}' with this input was already called. Use a different query or URL.]"
        else:
            seen_tool_calls.update(dedup_keys)
            parsed_args, output = _execute_emulated_tool(tool_name, args_string)

        results.append((normalized_name, parsed_args["kwargs"], output))
    return results


class LocalHistoryAdapter:
    def __init__(self, runner_obj, session_id):
        self.runner_obj = runner_obj
        self.session_id = session_id

    def get_openai_messages(
        self,
        sys_inst: str,
        rag_context: str,
        memory_context: str = None,
        response_only: bool = False
    ) -> list:
        raise NotImplementedError()

    def append_assistant_message(self, text: str, tool_calls_data: list, invocation_id: str):
        raise NotImplementedError()

    def append_tool_events(self, results: list, invocation_id: str):
        raise NotImplementedError()

    def append_image_tool_events(self, tool_name: str, tool_args: dict, new_markdown: str, call_id: str, invocation_id: str):
        raise NotImplementedError()

    def post_process_thoughts(self, invocation_id: str):
        raise NotImplementedError()


class LocalOffloadTrigger(Exception):
    def __init__(self, reason, iteration):
        self.reason = reason
        self.iteration = iteration


def _get_safe_local_path(image_url: str) -> str:
    """Converts an image URL into a local path relative to the workspace,
    supporting subdirectories like 'portraits'.
    """
    if "/images/" not in image_url:
        return None
    filename = image_url.split("/images/")[-1]
    filename = filename.replace("\\", "/").strip("/")
    parts = filename.split("/")
    safe_parts = []
    for p in parts:
        safe_p = "".join(c for c in p if c.isalnum() or c in "._-")
        if safe_p:
            safe_parts.append(safe_p)
    if not safe_parts:
        return None
    active_follower = get_active_follower()
    return os.path.normpath(os.path.join("core", "followers", active_follower, *safe_parts))


def _extract_media(text: str, image_url: str = None, tool_calls: list = None) -> tuple[list, str]:
    """Extract media entries and clean markdown images from a stored message."""
    media = []

    def add_markdown_images(source_text: str):
        for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', source_text or ''):
            url = match.group(2)
            media_type = 'video' if url.lower().endswith('.mp4') else 'image'
            if url not in [item['url'] for item in media]:
                media.append({'url': url, 'type': media_type})

    add_markdown_images(text)
    clean_text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text or '').strip()

    if image_url and not image_url.startswith('data:'):
        media_type = 'video' if image_url.lower().endswith('.mp4') else 'image'
        if image_url not in [item['url'] for item in media]:
            media.append({'url': image_url, 'type': media_type})

    for tool_call in tool_calls or []:
        if tool_call.get('type') == 'response':
            add_markdown_images(tool_call.get('response', '') or '')

    return media, clean_text


def fallback_system_to_user_messages(messages: list) -> list:
    """Helper to convert and merge 'system' messages to 'user' messages
    if the local model server's chat template doesn't support the system role.
    """
    if not messages:
        return messages
    mapped_messages = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            mapped_messages.append({"role": "user", "content": f"[System Directive]\n{content}"})
        else:
            mapped_messages.append({"role": role, "content": content})
            
    return _merge_consecutive_messages(mapped_messages)


def strip_narration(text: str) -> str:
    """Removes first-person/third-person action narration in asterisks from the text.
    Preserves text inside double asterisks (bold text) and strips single asterisk action phrases.
    Also removes thoughts blocks inside <think>...</think> tags if any.
    """
    if not text:
        return ""
    
    # 1. Clean <think>...</think> and <|channel|>thought...<channel|> blocks first (handles closed and unclosed tags)
    text = re.sub(r'(?:<think>|\[think\]|<thought>|\[thought\]|<\|thought\|>|<\|channel\|>thought|<channel\|>thought)[\s\S]*?(?:</think>|\[/think\]|</thought>|\[/thought\]|<\|/thought\|>|<\|channel\|>|<channel\|>|<\/\s*think>|\[\s*/\s*think\s*\]|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<\|channel\|>|<channel\|>', '', text, flags=re.IGNORECASE)
    
    # 2. Strip single asterisks action narration, e.g. *giggles* or *I pull you close*
    pattern = re.compile(r'(?<!\*)\*(?!\*)([\s\S]*?)(?<!\*)\*(?!\*)')
    text = pattern.sub('', text)
    
    # 3. Clean up any residual single asterisks that might get orphaned
    text = re.sub(r'(?<!\*)\*(?!\*)', '', text)
    
    # 4. Clean up spacing and newlines
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text.strip()

def _sanitize_tool_arg(val):
    if val is Ellipsis:
        return None
    if isinstance(val, dict):
        return {k: _sanitize_tool_arg(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_sanitize_tool_arg(v) for v in val]
    return val


def _parse_emulated_tool_call(tool_name: str, args_str: str) -> dict:
    """Parses arguments from an emulated tool call string.
    Supports both key=value style and simple positional string style.
    """
    import ast
    try:
        parsed = ast.parse(f"dummy({args_str})")
        call_node = parsed.body[0].value
        kwargs = {}
        args = []
        for kw in call_node.keywords:
            kwargs[kw.arg] = _sanitize_tool_arg(ast.literal_eval(kw.value))
        for arg in call_node.args:
            args.append(_sanitize_tool_arg(ast.literal_eval(arg)))
        return {"args": args, "kwargs": kwargs}
    except Exception:
        kwargs = {}
        kv_pairs = re.findall(r'(\w+)\s*=\s*(["\'])(.*?)\2', args_str)
        if kv_pairs:
            for k, _, v in kv_pairs:
                kwargs[k] = v
            return {"args": [], "kwargs": kwargs}
        
        val = args_str.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        return {"args": [_sanitize_tool_arg(val)], "kwargs": {}}


def _convert_json_tool_calls_to_tags(text: str) -> str:
    """Detects JSON formatted tool calls from any model
    and converts them to the standard [tool_name(args)] tag format.
    """
    if not text or "action" not in text or "action_input" not in text:
        return text
    import re, json, tools.tools as tools
    i = 0
    while i < len(text):
        if text[i] == '{':
            depth = 1
            j = i + 1
            while j < len(text) and depth > 0:
                if text[j] == '{': depth += 1
                elif text[j] == '}': depth -= 1
                j += 1
            if depth == 0:
                block = text[i:j]
                if "action" in block and "action_input" in block:
                    try:
                        d = json.loads(block)
                        act = d.get("action")
                        inp = d.get("action_input")
                        if act and isinstance(act, str) and inp is not None:
                            norm_act = _normalize_tool_name(act)
                            
                            # Dynamically verify if this tool is registered or exists
                            if hasattr(tools, norm_act) or norm_act in ("generate_local_image", "generate_imagen"):
                                if isinstance(inp, str) and inp.strip().startswith("{"):
                                    try: inp = json.loads(inp)
                                    except: pass
                                    
                                # Format arguments dynamically
                                args_list = []
                                if isinstance(inp, dict):
                                    for k, v in inp.items():
                                        if isinstance(v, str):
                                            escaped_v = v.replace('\\', '\\\\').replace('"', '\\"')
                                            args_list.append(f'{k}="{escaped_v}"')
                                        else:
                                            args_list.append(f'{k}={v}')
                                elif isinstance(inp, str):
                                    escaped_v = inp.replace('\\', '\\\\').replace('"', '\\"')
                                    args_list.append(f'prompt="{escaped_v}"')
                                    
                                args_str = ", ".join(args_list)
                                tag = f"[{norm_act}({args_str})]"
                                
                                start, end = i, j
                                pre = text[max(0, start-15):start]
                                suf = text[end:min(len(text), end+15)]
                                m_start = re.search(r'```(?:json)?\s*$', pre, re.IGNORECASE)
                                m_end = re.match(r'^\s*```', suf, re.IGNORECASE)
                                if m_start and m_end:
                                    start -= len(m_start.group(0))
                                    end += len(m_end.group(0))
                                    
                                text = text[:start] + tag + text[end:]
                                i = -1
                    except Exception:
                        pass
        i += 1
    return text