import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SAVES_DIR = BASE_DIR / "variables" / "saves"
ACTIVE_SAVE_FILE = BASE_DIR / "variables" / "active_save.json"

DEFAULT_GREETING = (
    "A spectral vision coalesces before your eyes in the damp dark of your cell. "
    "The shimmering, ethereal form of Ria Silmane appears, reaching out with gentle urgency.\n\n"
    "\"Can you hear me? Jagar Tharn has betrayed us all. He has imprisoned Emperor Uriel Septim in Oblivion "
    "and usurped the Imperial throne with powerful illusion. He murdered me when I discovered his treachery, "
    "but my spirit endures to guide you. You must escape this dungeon! In the southwest corner lies a magical Shift Gate. "
    "I have broken the lock on your cell door. Move swiftly, and may the Divines watch over you!\""
)


def get_active_save_id() -> str:
    """Return the active save directory name."""
    if ACTIVE_SAVE_FILE.exists():
        try:
            with open(ACTIVE_SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                save_id = data.get("active_save_id")
                if save_id and (SAVES_DIR / save_id).exists():
                    return save_id
        except Exception:
            pass
    
def get_save_directory(save_id: str = None) -> Path:
    """Return absolute Path object to a save directory."""
    if not save_id:
        save_id = get_active_save_id()
    path = SAVES_DIR / save_id
    path.mkdir(parents=True, exist_ok=True)
    return path

    # Default fallback
    default_id = "eternal_champion"
    if not (SAVES_DIR / default_id).exists():
        (SAVES_DIR / default_id).mkdir(parents=True, exist_ok=True)
    return default_id


def set_active_save_id(save_id: str) -> None:
    """Set the active save directory name."""
    ACTIVE_SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIVE_SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump({"active_save_id": save_id}, f, indent=2)


def sync_save_meta(save_id: str) -> dict:
    """Read character sheet and world state to update or generate meta.json."""
    save_path = SAVES_DIR / save_id
    if not save_path.exists():
        return {}
        
    char_path = save_path / "character_sheet.json"
    world_path = save_path / "world_state.json"
    meta_path = save_path / "meta.json"
    
    char = {}
    if char_path.exists():
        try:
            with open(char_path, "r", encoding="utf-8") as f:
                char = json.load(f)
        except Exception:
            pass
            
    world = {}
    if world_path.exists():
        try:
            with open(world_path, "r", encoding="utf-8") as f:
                world = json.load(f)
        except Exception:
            pass
            
    existing_meta = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                existing_meta = json.load(f)
        except Exception:
            pass

    t_date = world.get("tamrielic_date", {})
    date_str = f"{t_date.get('day', 1)} {t_date.get('month', 'Morning Star')}, 3E {t_date.get('year', 389)}"

    user_profile_id = save_id

    meta = {
        "id": save_id,
        "name": existing_meta.get("name") or char.get("name", "Eternal Champion"),
        "user_profile_id": user_profile_id,
        "created_at": existing_meta.get("created_at", datetime.now().isoformat()),
        "updated_at": datetime.now().isoformat(),
        "character_name": char.get("name", "Eternal Champion"),
        "race": char.get("race", "Nord"),
        "gender": char.get("gender", "Male"),
        "class": char.get("class", "Mage"),
        "level": char.get("level", 1),
        "gold": char.get("gold", 0),
        "current_province": world.get("current_province", "Cyrodiil"),
        "current_location": world.get("current_location", "Imperial Dungeon"),
        "quest_stage": world.get("quest_stage", 10),
        "tamrielic_date": date_str
    }
    
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)
        
    return meta


def list_saves() -> list:
    """Return list of all save metadata objects."""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    active_id = get_active_save_id()
    saves = []
    
    for item in SAVES_DIR.iterdir():
        if item.is_dir():
            save_id = item.name
            meta = sync_save_meta(save_id)
            if meta:
                # Ensure the player profile file exists inside the save folder
                profile_path = item / "profile.md"
                if not profile_path.exists():
                    try:
                        char_name = meta.get("character_name", "Eternal Champion")
                        race = meta.get("race", "Nord")
                        char_class = meta.get("class", "Mage")
                        gender = meta.get("gender", "Male")
                        default_content = f"# {char_name.upper()}\n- Race: {race}\n- Class: {char_class}\n- Gender: {gender}\n- Description: A brave adventurer.\n"
                        with open(profile_path, "w", encoding="utf-8") as f:
                            f.write(default_content)
                    except Exception as e:
                        print(f"Error auto creating profile.md in save {save_id}: {e}")
                
                meta["is_active"] = (save_id == active_id)
                saves.append(meta)
                
    # Sort with active save first, then newest updated
    saves.sort(key=lambda s: (not s.get("is_active", False), s.get("updated_at", "")), reverse=False)
    return saves


def create_save(name: str = None, character_name: str = "Eternal Champion", race: str = "Nord", gender: str = "Male", character_class: str = "Mage", user_profile_id: str = None, save_id: str = None) -> dict:
    """Create an isolated, complete new save state locked to a player profile."""
    if not save_id:
        timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c for c in (character_name or "hero").lower() if c.isalnum() or c in "_-")
        save_id = f"{clean_name}_{timestamp_slug}"
        
    save_path = SAVES_DIR / save_id
    save_path.mkdir(parents=True, exist_ok=True)

    if not user_profile_id:
        user_profile_id = save_id
    
    # Ensure player profile file exists inside the save path
    profile_path = save_path / "profile.md"
    if not profile_path.exists():
        try:
            default_content = f"# {character_name.upper()}\n- Race: {race}\n- Class: {character_class}\n- Gender: {gender}\n- Description: A brave adventurer.\n"
            with open(profile_path, "w", encoding="utf-8") as f:
                f.write(default_content)
        except Exception as e:
            print(f"Error auto creating user profile file: {e}")

    # 1. Initialize character sheet
    from engine.character import DEFAULT_SHEET, update_character_identity
    import copy
    sheet = copy.deepcopy(DEFAULT_SHEET)
    sheet = update_character_identity(sheet, name=character_name, race=race, gender=gender, character_class=character_class, reset_vitals=True)
    with open(save_path / "character_sheet.json", "w", encoding="utf-8") as f:
        json.dump(sheet, f, indent=4, ensure_ascii=False)
        
    # 2. Initialize world state
    default_world_path = BASE_DIR / "core" / "world" / "world_state.json"
    if default_world_path.exists():
        with open(default_world_path, "r", encoding="utf-8") as f:
            world_state = json.load(f)
    else:
        world_state = {
            "tamrielic_date": {"day": 1, "month": "Morning Star", "year": 389, "era": "Third Era"},
            "current_province": "Cyrodiil",
            "current_location": "Imperial Dungeon",
            "quest_stage": 10,
            "fragments_collected": [],
            "provinces_visited": ["Cyrodiil"],
            "cities_discovered": [],
            "dungeons_cleared": [],
            "world_flags": {"shift_gate_answered": False, "ria_vision_1_seen": True}
        }
    with open(save_path / "world_state.json", "w", encoding="utf-8") as f:
        json.dump(world_state, f, indent=4, ensure_ascii=False)
        
    # 3. Initialize narrative chat history
    from core.program_config import get_program_greeting, replace_placeholders
    opening_mes = replace_placeholders(get_program_greeting(), user_name=character_name)
    import uuid
    first_msg_id = f"first_mes_{uuid.uuid4().hex[:12]}"
    history_data = {
        "messages": [
            {
                "id": first_msg_id,
                "role": "program",
                "text": opening_mes,
                "content": opening_mes
            }
        ]
    }
    with open(save_path / "history.json", "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2, ensure_ascii=False)
        
    # 4. Save metadata
    meta = {
        "id": save_id,
        "name": name or f"{character_name} - {race} {character_class}",
        "user_profile_id": user_profile_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "character_name": character_name,
        "race": race,
        "gender": gender,
        "class": character_class,
        "level": 1,
        "gold": sheet.get("gold", 75),
        "current_province": "Cyrodiil",
        "current_location": "Imperial Dungeon",
        "quest_stage": 10,
        "tamrielic_date": "1 Morning Star, 3E 389"
    }
    with open(save_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)
        
    # Set as active save and sync player profile
    set_active_save_id(save_id)
    from utils.program import set_active_user
    set_active_user(user_profile_id)
    meta["is_active"] = True
    return meta


def load_save(save_id: str) -> dict:
    """Activate a save state by ID and lock active user profile to its associated character."""
    save_path = SAVES_DIR / save_id
    if not save_path.exists():
        raise FileNotFoundError(f"Save {save_id} does not exist.")
        
    set_active_save_id(save_id)
    meta = sync_save_meta(save_id)
    
    # Automatically sync active user profile to this save's profile
    user_prof = meta.get("user_profile_id") or save_id
    from utils.program import set_active_user
    set_active_user(user_prof)
    
    meta["is_active"] = True
    return meta


def reset_save_to_defaults(save_id: str) -> dict:
    """Reset a save state to a pristine default state."""
    save_path = SAVES_DIR / save_id
    save_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Retrieve character metadata from current save if possible, otherwise defaults
    meta_path = save_path / "meta.json"
    character_name = save_id.replace("_", " ").title()
    race = "Nord"
    gender = "Male"
    character_class = "Battlemage" if save_id == "eternal_champion" else "Mage"
    user_profile_id = save_id
    
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                character_name = meta.get("character_name", character_name)
                race = meta.get("race", race)
                gender = meta.get("gender", gender)
                character_class = meta.get("class", character_class)
                user_profile_id = meta.get("user_profile_id", user_profile_id)
        except Exception:
            pass
            
    # 2. Reset character sheet
    from engine.character import DEFAULT_SHEET, update_character_identity
    import copy
    sheet = copy.deepcopy(DEFAULT_SHEET)
    sheet = update_character_identity(sheet, name=character_name, race=race, gender=gender, character_class=character_class, reset_vitals=True)
    with open(save_path / "character_sheet.json", "w", encoding="utf-8") as f:
        json.dump(sheet, f, indent=4, ensure_ascii=False)
        
    # 3. Reset world state
    default_world_path = BASE_DIR / "core" / "world" / "world_state.json"
    if default_world_path.exists():
        with open(default_world_path, "r", encoding="utf-8") as f:
            world_state = json.load(f)
    else:
        world_state = {
            "tamrielic_date": {"day": 1, "month": "Morning Star", "year": 389, "era": "Third Era"},
            "current_province": "Cyrodiil",
            "current_location": "Imperial Dungeon",
            "quest_stage": 10,
            "fragments_collected": [],
            "provinces_visited": ["Cyrodiil"],
            "cities_discovered": [],
            "dungeons_cleared": [],
            "world_flags": {"shift_gate_answered": False, "ria_vision_1_seen": True}
        }
    with open(save_path / "world_state.json", "w", encoding="utf-8") as f:
        json.dump(world_state, f, indent=4, ensure_ascii=False)
        
    # 4. Reset history
    from core.program_config import get_program_greeting, replace_placeholders
    opening_mes = replace_placeholders(get_program_greeting(), user_name=character_name)
    import uuid
    first_msg_id = f"first_mes_{uuid.uuid4().hex[:12]}"
    history_data = {
        "messages": [
            {
                "id": first_msg_id,
                "role": "program",
                "text": opening_mes,
                "content": opening_mes
            }
        ]
    }
    with open(save_path / "history.json", "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2, ensure_ascii=False)
        
    # 5. Reset metadata json
    meta = {
        "id": save_id,
        "name": f"{character_name} - {race} {character_class}",
        "user_profile_id": user_profile_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "character_name": character_name,
        "race": race,
        "gender": gender,
        "class": character_class,
        "level": 1,
        "gold": sheet.get("gold", 75),
        "current_province": "Cyrodiil",
        "current_location": "Imperial Dungeon",
        "quest_stage": 10,
        "tamrielic_date": "1 Morning Star, 3E 389"
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)
        
    return meta


def reset_default_save() -> dict:
    """Reset the eternal_champion save to a pristine default state."""
    return reset_save_to_defaults("eternal_champion")


def delete_save(save_id: str, force_delete: bool = False) -> bool:
    """Reset a save state, or permanently delete its folder if force_delete is True."""
    if not force_delete:
        reset_save_to_defaults(save_id)
        return True

    if save_id == "eternal_champion":
        reset_save_to_defaults("eternal_champion")
        return True

    save_path = SAVES_DIR / save_id
    if not save_path.exists():
        return False
        
    shutil.rmtree(save_path, ignore_errors=True)
    
    # If deleted save was active, switch to eternal_champion
    if get_active_save_id() == save_id:
        remaining = [item.name for item in SAVES_DIR.iterdir() if item.is_dir()]
        if remaining:
            set_active_save_id(remaining[0])
        else:
            reset_save_to_defaults("eternal_champion")
            set_active_save_id("eternal_champion")
            
    return True
