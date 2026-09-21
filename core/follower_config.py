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

# Formatting rules for The Game (World referee & narrator)
GAME_FORMATTING = (
    "\n\n# NARRATION STYLE RULES (MANDATORY)\n"
    "- Narration: Wrap EVERY paragraph and sentence of environmental description, sensory detail, NPC action, and world outcomes in *asterisks*.\n"
    "- World NPCs & Questgivers: You portray enemies, creatures, questgivers, guards, and non-party world NPCs. Wrap their physical actions in *asterisks* and output their spoken speech in plain text without quotation marks.\n"
    "- Party Followers: Traveling party members speak and act independently on their own turns. Generate zero dialogue, zero spoken quotes, zero reactions, and zero actions for party followers. Leave all follower responses to the follower's turn.\n"
    "- Claims: State all claims directly and affirmatively in single assertions.\n"
    "- Style: Use short words and precise phrasing. Write with linear progression.\n"
    "- Be succinct, atmospheric, and faithful to Elder Scrolls lore.\n"
)

# Global formatting rules for narrative roleplay (Followers)
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
    fol_dir = os.path.join(FOLLOWERS_DIR, follower_id)
    if os.path.isdir(fol_dir):
        for fname in os.listdir(fol_dir):
            if fname.endswith(".json") and not fname.endswith("_voice.json"):
                try:
                    with open(os.path.join(fol_dir, fname), "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    return raw.get("data", raw)
                except Exception as e:
                    logging.error(f"Error loading follower card file '{fname}': {e}")
    return {}


def get_follower_image_details(follower_id: str = None, card: dict = None) -> tuple[str, str]:
    """Returns (positive_prompt, negative_prompt) from the follower's card."""
    if card is None:
        card = _load_card_data(follower_id)
    if not card:
        return "", ""

    exts = card.get("extensions") or {}
    arena = exts.get("arena") or exts.get("sanctuary") or {}
    details = arena.get("image_details") or {}
    pos = details.get("positive") or ""
    neg = details.get("negative") or ""

    if not pos and not neg:
        top_details = card.get("image_details") or {}
        pos = top_details.get("positive") or ""
        neg = top_details.get("negative") or ""

    if not pos:
        pos = card.get("image_positive") or ""
    if not neg:
        neg = card.get("image_negative") or ""

    return str(pos).strip(), str(neg).strip()


def match_follower_by_full_name(text: str, candidate_ids: list[str] = None) -> str | None:
    """Scans text for followers' full names (case-insensitive) and returns the matched follower ID."""
    if not text:
        return None

    from runners.follower import get_active_followers
    active_ids = list(candidate_ids) if candidate_ids is not None else list(get_active_followers())

    clean_text = text.lower()
    for fid in active_ids:
        if fid in ("game", "the_game"):
            continue
        fname = get_follower_name(fid).strip().lower()
        if fname and re.search(rf"\b{re.escape(fname)}\b", clean_text):
            return fid

    if os.path.exists(FOLLOWERS_DIR):
        for entry in os.listdir(FOLLOWERS_DIR):
            if entry in ("game", "the_game") or entry in active_ids:
                continue
            if os.path.isdir(os.path.join(FOLLOWERS_DIR, entry)):
                fname = get_follower_name(entry).strip().lower()
                if fname and re.search(rf"\b{re.escape(fname)}\b", clean_text):
                    return entry

    return None


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


def replace_placeholders(text: str, user_name: str = None, follower_id: str = None, party_followers: list = None) -> str:
    """Replaces {{user}}, {{char1}}, {{char2}}, {{char3}}, and {{char}} placeholders with actual names."""
    if not text:
        return text
    if not user_name:
        user_name = get_player_name()

    from runners.follower import get_active_followers
    party = party_followers if party_followers is not None else get_active_followers()

    char1_name = get_follower_name(party[0]) if len(party) > 0 else ""
    char2_name = get_follower_name(party[1]) if len(party) > 1 else ""
    char3_name = get_follower_name(party[2]) if len(party) > 2 else ""

    if follower_id and follower_id not in ("game", "the_game"):
        char_name = get_follower_name(follower_id)
    else:
        char_name = char1_name or "Follower"

    party_names = [get_follower_name(fid) for fid in party if fid and fid not in ("game", "the_game", "none", "solo")]
    party_str = ", ".join(party_names) if party_names else "none"

    text = re.sub(r'(?i)\{\{user\}\}', user_name, text)
    text = re.sub(r'(?i)\{\{char1\}\}', char1_name, text)
    text = re.sub(r'(?i)\{\{char2\}\}', char2_name, text)
    text = re.sub(r'(?i)\{\{char3\}\}', char3_name, text)
    text = re.sub(r'(?i)\{\{char\}\}', char_name, text)
    text = re.sub(r'(?i)\{\{followers\}\}', party_str, text)
    text = re.sub(r'(?i)\{\{party\}\}', party_str, text)
    return text


def get_follower_greeting(follower_id: str = None) -> str:
    """Returns the follower's first message from card data with a sensible fallback."""
    if not follower_id:
        follower_id = get_active_follower()
    card = _load_card_data(follower_id)
    first_mes = card.get("first_mes")
    if first_mes:
        return replace_placeholders(first_mes, follower_id=follower_id)
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
        prompt_parts.append(f"## ACTIVE SCENARIO & SETTING\n{scenario}")

    mes_example = (card.get("mes_example") or "").strip()
    if mes_example:
        prompt_parts.append(f"## DIALOGUE EXAMPLES\n{mes_example}")

    system_prompt = card.get("system_prompt", "").strip()
    if system_prompt:
        prompt_parts.append(f"## CORE INSTRUCTIONS\n{system_prompt}")

    post_history = card.get("post_history_instructions", "").strip()
    if post_history:
        prompt_parts.append(f"## ROLEPLAY GUIDELINES\n{post_history}")

    visual, _ = get_follower_image_details(card=card)
    if visual:
        prompt_parts.append(f"## APPEARANCE\n{visual}")

    return "\n\n".join(prompt_parts)


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
        logging.error(f"[follower_config] Error retrieving toolbelt: {e}")

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
    """Loads player-specific persona and directives."""
    return f"\n\n# PLAYER PROFILE\n- Hero: {get_player_name()}\n"


def compile_speaker_instructions(speaker_id: str = "game", follower_id: str = None, party_followers: list = None) -> str:
    """Compiles a complete system prompt specifically for the active speaker (Game or Follower)."""
    from utils.utils import _ARENA_DIRECTIVE_PROMPT
    player_name = get_player_name()
    
    from runners.follower import get_active_followers
    party = party_followers if party_followers is not None else get_active_followers()
    active_target = follower_id
    if active_target and active_target not in ("game", "none", "solo") and active_target not in party:
        party = [active_target] + [p for p in party if p != active_target][:2]

    party_names = [get_follower_name(fid) for fid in party]

    party_follower_entries = []
    party_follower_all_names = []
    for fid in party:
        fname = get_follower_name(fid)
        party_follower_all_names.append(fname)
        first_name = fname.split()[0]
        if first_name != fname:
            party_follower_all_names.append(first_name)
            party_follower_entries.append(f"{fname} (also called {first_name}, ID: {fid})")
        else:
            party_follower_entries.append(f"{fname} (ID: {fid})")

    party_list_str = ", ".join(party_follower_entries) if party_follower_entries else "None (traveling solo)"
    party_names_str = ", ".join(dict.fromkeys(party_follower_all_names)) if party_follower_all_names else "none"

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

        referee_block = (
            f"\n\n# REFEREE ROLE DIRECTIVE (MANDATORY)\n"
            f"You are The Game, the world referee and narrator.\n"
            f"- Hero: {player_name}.\n"
            f"- Active Party Followers: {party_list_str}.\n"
            f"- World Authority: You narrate world environments, sensory details, dungeon hazards, and results of actions.\n"
            f"- World NPCs & Creatures: You portray enemies, creatures, questgivers, guards, and townspeople.\n"
            f"- STRICT FOLLOWER AUTONOMY: Traveling party members ({party_names_str}) and {player_name} are independent characters who speak and act on their own turns.\n"
            f"- ZERO FOLLOWER PUPPETING: Never write speech, dialogue, quotes, thoughts, physical actions, or reactions for {player_name} or ANY follower ({party_names_str}).\n"
            f"- When {player_name} speaks to, looks at, touches, or interacts with a follower, describe ONLY the physical environment, dungeon conditions, or world NPC reactions. Conclude your turn immediately so the follower can respond for themselves."
        )

        base = game_instructions + load_user_instructions()
        base += referee_block
        base += _ARENA_DIRECTIVE_PROMPT
        base += GAME_FORMATTING
        base += load_dynamic_runtime_context()
        return replace_placeholders(base, party_followers=party)

    else:
        # Speaker is a Follower (e.g. riasilmane, breamaccius)
        card = _load_card_data(speaker_id)
        follower_name = card.get("name") if card else speaker_id.replace("_", " ").title()
        follower_instructions = compile_instructions_from_card(card) if card else f"# IDENTITY: {follower_name}\n"

        other_followers = [fn for fn in party_names if fn != follower_name]
        follower_context = f"- Fellow Followers: {', '.join(other_followers)}.\n" if other_followers else ""

        follower_block = (
            f"\n\n# FOLLOWER ROLE DIRECTIVES (MANDATORY)\n"
            f"You are {follower_name}, a follower traveling alongside {player_name}.\n"
            f"- Active Speaker: You ({follower_name}).\n"
            f"{follower_context}"
            f"- Deliver only {follower_name}'s spoken dialogue, physical gestures, emotions, and personal reactions.\n"
            f"- Speak and act strictly from {follower_name}'s perspective and character persona.\n"
            f"- Converse directly with {player_name}{(' and ' + ', '.join(other_followers)) if other_followers else ''}.\n"
            f"- In exploration, speak, observe, and advise. Leave physical actions on the world to {player_name}.\n"
            f"- The Game is the sole referee and narrator of the world. The Game narrates all story progression, environmental changes, dungeon mechanics, and player action outcomes.\n"
            f"- React to the events and outcomes already established by The Game and {player_name}.\n"
            f"- Never narrate world outcomes, scenery changes, lock/door results, combat resolution, or the consequences of {player_name}'s actions."
        )

        base = replace_placeholders(follower_instructions + load_user_instructions(), follower_id=speaker_id, party_followers=party)
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
