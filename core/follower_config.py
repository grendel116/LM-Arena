import datetime
import json
import logging
import os
import re
import sys

# Ensure parent directory is in sys.path
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from variables.settings import FOLLOWERS_DIR, SAVES_DIR
from runners.follower import get_active_follower, get_active_user, get_player_name

# Global formatting rules for narrative roleplay
GLOBAL_FORMATTING = (
    "\n\n# MESSAGE FORMAT & STYLING RULES (MANDATORY)\n"
    "- Narration: Wrap EVERY paragraph, sentence, and phrase of narration, action, expression, physical movement, and environmental detail in *asterisks* (e.g. *The wall is slick with moisture, and the ledge sits high above.*).\n"
    "- Dialogue: Output spoken speech in plain text without quotation marks and without asterisks (e.g. I am Ria Silmane. We must act quickly.). Use **bold** only for vocal emphasis.\n"
    "- Paragraph Separation: Keep narration and dialogue separated into distinct, separate lines and paragraphs.\n"
    "- Claims: State all claims directly and affirmatively in single assertions.\n"
    "- FORBIDDEN: Do not use contrast structures ('not X, but Y', 'it is not A, it is B', 'not just X, it is Y'). Express ideas positively without negating alternatives.\n"
    "- Style: Use short words and precise phrasing. Write with linear progression.\n"
    "- Be succinct, atmospheric, and faithful to Elder Scrolls lore and character persona.\n"
)


GLOBAL_USER_FORMATTING = GLOBAL_FORMATTING


def _load_card_data(follower_id: str) -> dict:
    """Loads the follower's chara_card_v3 JSON or card dictionary."""
    if not follower_id:
        follower_id = get_active_follower()
    json_path = os.path.join(FOLLOWERS_DIR, follower_id, f"{follower_id}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw.get("data", raw)
        except Exception as e:
            logging.error(f"Error loading follower card for '{follower_id}': {e}")
    return {}


def get_follower_name(follower_id: str = None) -> str:
    """Returns the follower's character name."""
    if not follower_id:
        follower_id = get_active_follower()
    card = _load_card_data(follower_id)
    return card.get("name") or follower_id.replace("_", " ").title()


def follower_name() -> str:
    """Alias for get_follower_name for backwards compatibility."""
    return get_follower_name()


def replace_placeholders(text: str, user_name: str = None, follower_id: str = None) -> str:
    """Replaces {{user}} and {{char}} placeholders with actual names."""
    if not text:
        return text
    if not user_name:
        user_name = get_player_name()
    try:
        char_name = get_follower_name(follower_id)
    except Exception:
        char_name = "Follower"

    text = re.sub(r'(?i)\{\{user\}\}', user_name, text)
    text = re.sub(r'(?i)\{\{char\}\}', char_name, text)
    return text


def get_follower_greeting(follower_id: str = None) -> str:
    """Returns the follower's first message from card data with a sensible fallback."""
    if not follower_id:
        follower_id = get_active_follower()
    card = _load_card_data(follower_id)
    first_mes = card.get("first_mes")
    if first_mes:
        return first_mes
    return f"Greetings, {get_player_name()}. I stand ready to assist you in Tamriel."


def compile_instructions_from_card(card: dict) -> str:
    """Compiles character card fields into a cohesive system instruction block."""
    prompt_parts = []
    
    name = card.get("name", "").strip()
    if name:
        prompt_parts.append(f"# CHARACTER IDENTITY: {name}")

    description = card.get("description", "").strip()
    if description:
        prompt_parts.append(f"## DESCRIPTION & BACKGROUND\n{description}")

    personality = card.get("personality", "").strip()
    if personality:
        prompt_parts.append(f"## PERSONALITY & TRAITS\n{personality}")

    scenario = card.get("scenario", "").strip()
    if scenario:
        prompt_parts.append(f"## SCENARIO & CONTEXT\n{scenario}")

    mes_example = (card.get("mes_example") or "").strip()
    if mes_example:
        prompt_parts.append(f"## DIALOGUE EXAMPLES\n{mes_example}")

    system_prompt = card.get("system_prompt", "").strip()
    if system_prompt:
        prompt_parts.append(f"## SPECIAL INSTRUCTIONS\n{system_prompt}")

    return replace_placeholders("\n\n".join(prompt_parts))


def compile_instructions_from_json(card_json: dict) -> str:
    """Alias for compile_instructions_from_card."""
    data = card_json.get("data", card_json) if isinstance(card_json, dict) else {}
    return compile_instructions_from_card(data)


def load_static_instructions(follower_id: str = None) -> str:
    """Reads the active follower's card and compiles it into a system prompt.
    Also appends available toolbelt capabilities.
    """
    if not follower_id:
        follower_id = get_active_follower()
    card = _load_card_data(follower_id)
    if card:
        instruction_content = compile_instructions_from_card(card)
    else:
        instruction_content = f"# FOLLOWER: {follower_id.replace('_', ' ').title()}\n"
        
    try:
        from core.skill_retriever import get_toolbelt_block
        toolbelt = get_toolbelt_block()
        if toolbelt:
            instruction_content += "\n\n" + toolbelt
    except Exception as e:
        logging.error(f"[follower_config] Error loading toolbelt: {e}")

    return instruction_content


def load_dynamic_runtime_context() -> str:
    """Compiles environment parameters for runtime grounding without minute-level cache invalidation."""
    env_block = (
        "### SYSTEM ENVIRONMENT CONTEXT\n"
        "- Active Engine: LM-Arena Local LLM Runner\n"
        "- Host OS: Windows\n"
    )
    return f"\n\n# DYNAMIC RUNTIME CONTEXT\n{env_block}"


def load_user_instructions() -> str:
    """Reads the active player profile context from the save file."""
    try:
        from core.save_manager import read_save
        bundle = read_save()
        profile_content = (bundle.get("profile") or "").strip()
        if profile_content:
            return f"\n\n# PLAYER PROFILE\n{profile_content}\n"
    except Exception as e:
        logging.error(f"Error reading profile from save: {e}")

    return f"\n\n# PLAYER PROFILE\n- Hero: {get_player_name()}\n"


def get_compiled_instructions(follower_id: str = None) -> str:
    """Merges follower card instructions, player profile context, formatting, and runtime context."""
    base = replace_placeholders(load_static_instructions(follower_id) + load_user_instructions())
    base += GLOBAL_FORMATTING
    base += load_dynamic_runtime_context()
    return base


# Sanitized identifier for agent initialization
sanitized_agent_name = re.sub(r'[^a-zA-Z0-9_]', '_', get_follower_name())
if not sanitized_agent_name or not (sanitized_agent_name[0].isalpha() or sanitized_agent_name[0] == '_'):
    sanitized_agent_name = '_' + sanitized_agent_name

instruction = get_compiled_instructions()
