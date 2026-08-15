import datetime
import logging
import os
import re
import shutil
import sys


# Ensure the parent directory is in sys.path so we can import variables package
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from variables import DEFAULT_REMOTE_MODEL, PROGRAMS_DIR

# --- SYSTEM CONTEXT COMPILER ---

def _load_card_data(program_id: str) -> dict:
    """Loads the program's chara_card_v3 JSON and returns the data block."""
    import json
    json_path = os.path.join(PROGRAMS_DIR, program_id, f"{program_id}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw.get("data", raw)
        except Exception as e:
            print(f"Error loading card for '{program_id}': {e}")
    return {}

def get_program_name() -> str:
    """Returns the active program's character name."""
    from utils.program import get_active_program
    active_program = get_active_program()
    card = _load_card_data(active_program)
    # v3: data.name / legacy: name
    return card.get("name") or active_program.title()

def replace_placeholders(text: str, user_name: str = None, comp_name: str = None) -> str:
    """Replaces {{user}} and {{char}} placeholders (case-insensitive) with their actual values."""
    if not text:
        return text
    if not user_name:
        from utils.program import get_active_user
        from engine.character import load_character
        active_id = get_active_user()
        try:
            user_sheet = load_character(active_id)
            user_name = user_sheet.get("name") or active_id.replace("_", " ").title()
        except Exception:
            user_name = active_id.replace("_", " ").title()
    if not comp_name:
        try:
            comp_name = get_program_name()
        except Exception:
            comp_name = "Program"
    
    text = re.sub(r'(?i)\{\{user\}\}', user_name, text)
    text = re.sub(r'(?i)\{\{char\}\}', comp_name, text)
    return text

def get_program_greeting() -> str:
    """Returns the program's first message from the card, with a default fallback."""
    from utils.program import get_active_program
    active_program = get_active_program()
    card = _load_card_data(active_program)
    # v3: data.first_mes / legacy: operation.example_message
    greeting = card.get("first_mes") or card.get("operation", {}).get("example_message", "")
    return greeting.strip() if greeting.strip() else "Hello, {{user}}."

def compile_instructions_from_card(card: dict) -> str:
    """Compiles a system prompt from a chara_card_v3 data block."""
    name = card.get("name", "Program")
    prompt_parts = [f"# IDENTITY: {name}"]

    description = card.get("description", "").strip()
    if description:
        prompt_parts.append(f"## CHARACTER\n{description}")

    personality = card.get("personality", "").strip()
    if personality:
        prompt_parts.append(f"## PERSONALITY\n{personality}")

    scenario = card.get("scenario", "").strip()
    if scenario:
        prompt_parts.append(f"## SCENARIO\n{scenario}")

    mes_example = (card.get("mes_example") or card.get("first_mes") or "").strip()
    if mes_example:
        prompt_parts.append(f"## EXAMPLE MESSAGE\n{mes_example}")

    system_prompt = card.get("system_prompt", "").strip()
    if system_prompt:
        prompt_parts.append(f"## RESPONSE INSTRUCTIONS\n{system_prompt}")

    return replace_placeholders("\n\n".join(prompt_parts))

def load_static_instructions() -> str:
    """Reads the active program's card and compiles it into a system prompt.
    Also appends all modular skill instructions.
    """
    from utils.program import get_active_program

    base_dir = os.path.dirname(os.path.abspath(__file__))
    active_program = get_active_program()

    card = _load_card_data(active_program)
    if card:
        instruction_content = compile_instructions_from_card(card)
    else:
        instruction_content = f"# NAME: {active_program.title()}\n"
            
    # Append compact toolbelt listing available capabilities
    # Full skill instructions are vector-retrieved per turn in runner_interface.py
    try:
        from core.skill_retriever import get_toolbelt_block
        toolbelt = get_toolbelt_block()
        if toolbelt:
            instruction_content += "\n\n" + toolbelt
    except Exception as e:
        print(f"[program_config] Error loading toolbelt: {e}")
            
    return instruction_content


def load_dynamic_runtime_context() -> str:
    """Compiles dynamic, time-sensitive system data points for runtime grounding."""
    now = datetime.datetime.now()
    return (
        "\n\n# RUNTIME CONTEXT\n"
        f"Local Time: {now.strftime('%Y-%m-%d %I:%M %p')} ({now.strftime('%A')})\n"
    )

def load_user_instructions() -> str:
    """Reads the active user profile configuration from the save JSON bundle to set private relationship context."""
    from utils.program import get_active_user
    from engine.save_manager import read_save
    active_profile = get_active_user()

    try:
        bundle = read_save(active_profile)
        content = bundle.get("profile", "").strip()
        if not content:
            meta = bundle.get("meta", {})
            race = meta.get("race", "Nord")
            content = f"A {race} from Skyrim."
        return f"\n\n# USER PROFILE & RELATIONSHIP CONTEXT\n{content}\n"
    except Exception as e:
        print(f"Failed to read user instructions: {e}")
        fallback_msg = "A Nord from Skyrim."
        return f"\n\n# USER PROFILE & RELATIONSHIP CONTEXT\n{fallback_msg}\n"



def get_compiled_instructions() -> str:
    """Merges static identity profiles, dynamic temporal/runtime contexts, and user relationship settings."""
    base = replace_placeholders(load_static_instructions() + load_user_instructions())

    global_formatting = (
        "\n\n# MESSAGE FORMAT\n"
        "- Use separate lines and clear paragraphs for narration and dialogue.\n"
        "- Narration: *italics*, present tense. Dialogue: plain text without quotes.\n"
        "- Gritty, kinetic atmosphere with anthropological depth and distinct character voices.\n"
        "- Do not end with questions, choices, or mirrored clauses.\n"
    )

    base += global_formatting
    base += load_dynamic_runtime_context()
    return base

# Determine program name dynamically from the active program configuration
program_name = get_program_name()

# LlmAgent requires the name to be a valid identifier. Sanitize it.
sanitized_agent_name = re.sub(r'[^a-zA-Z0-9_]', '_', program_name)
if not sanitized_agent_name or not (sanitized_agent_name[0].isalpha() or sanitized_agent_name[0] == '_'):
    sanitized_agent_name = '_' + sanitized_agent_name

# Dynamically initialize/reload the sovereign instruction
instruction = get_compiled_instructions()
