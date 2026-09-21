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
    if follower_id in ("game", "the_game"):
        return "The Game"
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

    visual = (
        card.get("extensions", {})
        .get("arena", card.get("extensions", {}).get("sanctuary", {}))
        .get("image_details", {})
        .get("positive", "")
        .strip()
    )
    if visual:
        prompt_parts.append(f"## APPEARANCE\n{visual}")

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


def compile_speaker_instructions(speaker_id: str = "game", follower_id: str = None, companion_id: str = None) -> str:
    """Compiles a complete system prompt specifically for the active speaker (Game or Follower)."""
    from utils.utils import _ARENA_DIRECTIVE_PROMPT
    player_name = get_player_name()
    active_follower_id = follower_id or companion_id

    if speaker_id == "game":
        card = _load_card_data("game")
        game_instructions = compile_instructions_from_card(card) if card else "# IDENTITY: The Game (Referee & Narrator)\n"
        
        try:
            from core.skill_retriever import get_toolbelt_block
            toolbelt = get_toolbelt_block()
            if toolbelt:
                game_instructions += "\n\n" + toolbelt
        except Exception as e:
            logging.error(f"[follower_config] Error loading toolbelt for Game: {e}")

        # Room / party context
        party_members = [f"{player_name} (Player)"]
        if active_follower_id and active_follower_id not in ("game", "none", "solo"):
            f_card = _load_card_data(active_follower_id)
            follower_name = f_card.get("name") if f_card else active_follower_id.replace("_", " ").title()
            party_members.append(f"{follower_name} (Follower)")
            follower_note = f"- Party Follower traveling with player: {follower_name}. Do NOT speak or choose actions for {follower_name}; they respond for themselves."
        else:
            follower_note = "- No followers currently in the traveling party. The player journeys alone through Tamriel."

        adjudication_block = (
            f"\n\n# TABLETOP ADJUDICATION ROSTER\n"
            f"- World Referee & Narrator: You (The Game).\n"
            f"- Traveling Party: {', '.join(party_members)}.\n"
            f"{follower_note}\n"
            f"- IDENTITY CONSTRAINT: You are The Game. You describe the world, direct monsters/NPCs, adjudicate rules, and call for skill checks.\n"
            f"- NEVER SPEAK FOR FOLLOWERS: Do not write dialogue, actions, reactions, or thoughts for {follower_name if active_follower_id and active_follower_id not in ('game', 'none', 'solo') else 'party followers'}. They speak for themselves.\n"
            f"- NEVER REPEAT FOLLOWER MESSAGES: Do not echo, re-state, or quote what party followers just said.\n"
            f"- NEVER PUPPET THE PLAYER: Do not write dialogue or decisions for {player_name}.\n"
            f"- NO SPEAKER TAGS: Do not output prefixes like '[Game]:', '[The Game]:', or '[{follower_name if active_follower_id and active_follower_id not in ('game', 'none', 'solo') else 'Follower'}]:'. Speak directly in third-person narrative.\n"
        )

        base = replace_placeholders(game_instructions + load_user_instructions())
        base += adjudication_block
        base += _ARENA_DIRECTIVE_PROMPT
        base += GLOBAL_FORMATTING
        base += load_dynamic_runtime_context()
        return base

    else:
        # Speaker is a Follower (e.g. ria_silmane)
        card = _load_card_data(speaker_id)
        follower_name = card.get("name") if card else speaker_id.replace("_", " ").title()
        follower_instructions = compile_instructions_from_card(card) if card else f"# IDENTITY: {follower_name}\n"

        follower_block = (
            f"\n\n# FOLLOWER ROLE DIRECTIVES (MANDATORY)\n"
            f"You are {follower_name}, a follower traveling alongside {player_name}.\n"
            f"- Active Speaker: You ({follower_name}).\n"
            f"- FOLLOWER ROLE: You are a follower offering counsel, lore, dialogue, and guidance. Never narrate the world or arbitrate game mechanics.\n"
            f"- IDENTITY & SCOPE CONSTRAINT: Speak and act EXCLUSIVELY as {follower_name}. Only describe your own immediate physical gestures, posture, expressions, and spoken words.\n"
            f"- DO NOT NARRATE THE SCENE OR ENVIRONMENT: Never describe dungeon rooms, corridors, surroundings, sounds, lighting, doors, or atmosphere not pertinent to your own body. All environment and scene narration belongs exclusively to The Game.\n"
            f"- DO NOT NARRATE THE PLAYER: Never describe {player_name}'s body movements, hands, footing, physical sensations, or attempted actions. {player_name} describes their own actions.\n"
            f"- DO NOT INTRODUCE YOURSELF: Do not narrate your arrival or describe your appearance in third person ('A woman emerges from the gloom...'). You are already present with {player_name}.\n"
            f"- NEVER ACT AS REFEREE: Do not resolve outcomes, do not narrate combat or consequences, and do not call for checks. The Game will adjudicate and resolve all actions immediately after your turn.\n"
            f"- NEVER PUPPET OTHERS: Do not write dialogue, reactions, or decisions for {player_name} or The Game.\n"
            f"- NO SPEAKER TAGS: Do not output prefixes like '[{follower_name}]:' or '{follower_name}:'. Speak directly in your own distinct character persona and voice.\n"
        )

        base = replace_placeholders(follower_instructions + load_user_instructions())
        base += follower_block
        base += GLOBAL_FORMATTING
        base += load_dynamic_runtime_context()
        return base


def get_compiled_instructions(follower_id: str = None) -> str:
    """Merges follower card instructions, player profile context, formatting, and runtime context."""
    target_speaker = follower_id or "game"
    return compile_speaker_instructions(target_speaker)


# Sanitized identifier for agent initialization
sanitized_agent_name = re.sub(r'[^a-zA-Z0-9_]', '_', get_follower_name())
if not sanitized_agent_name or not (sanitized_agent_name[0].isalpha() or sanitized_agent_name[0] == '_'):
    sanitized_agent_name = '_' + sanitized_agent_name

instruction = get_compiled_instructions()
