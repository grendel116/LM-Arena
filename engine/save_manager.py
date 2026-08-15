import json
import os
import re
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


def _get_clean_name(name: str) -> str:
    name_str = (name or "hero").lower().strip().replace(" ", "_").replace("-", "_")
    clean = "".join(c for c in name_str if c.isalnum() or c == "_")
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean or "hero"


def get_active_save_id() -> str:
    """Return the active save ID."""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    if ACTIVE_SAVE_FILE.exists():
        try:
            with open(ACTIVE_SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                save_id = data.get("active_save_id")
                if save_id:
                    json_path = SAVES_DIR / f"{save_id}.json"
                    dir_path = SAVES_DIR / save_id
                    if json_path.exists() or dir_path.exists():
                        return save_id
        except Exception:
            pass

    # Quick scan without calling list_saves to avoid recursion
    for item in sorted(SAVES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not item.name.startswith("."):
            return item.stem

    for item in sorted(SAVES_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if item.is_dir():
            return item.name

    return "eternal_champion_001"


def set_active_save_id(save_id: str) -> None:
    """Set the active save ID."""
    ACTIVE_SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIVE_SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump({"active_save_id": save_id}, f, indent=2)


def get_save_path(save_id: str = None) -> Path:
    """Return path to save file or legacy directory."""
    if not save_id:
        save_id = get_active_save_id()
    
    json_path = SAVES_DIR / f"{save_id}.json"
    if json_path.exists():
        return json_path
        
    dir_path = SAVES_DIR / save_id
    if dir_path.is_dir():
        return dir_path
        
    return json_path


def read_save(save_id: str = None) -> dict:
    """Read complete save bundle from single-file JSON or legacy directory."""
    if not save_id:
        save_id = get_active_save_id()
    
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    json_path = SAVES_DIR / f"{save_id}.json"
    dir_path = SAVES_DIR / save_id
    
    # 1. Single-file JSON save format
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"[read_save] Error reading single-file save {json_path}: {e}")

    # 2. Legacy directory save format
    if dir_path.is_dir():
        bundle = {
            "meta": {},
            "character": {},
            "world": {},
            "history": [],
            "memories": [],
            "databank": [],
            "profile": ""
        }
        
        char_f = dir_path / "character_sheet.json"
        if char_f.exists():
            try:
                bundle["character"] = json.load(open(char_f, "r", encoding="utf-8"))
            except Exception:
                pass
                
        world_f = dir_path / "world_state.json"
        if world_f.exists():
            try:
                bundle["world"] = json.load(open(world_f, "r", encoding="utf-8"))
            except Exception:
                pass
                
        hist_f = dir_path / "history.json"
        if hist_f.exists():
            try:
                h_data = json.load(open(hist_f, "r", encoding="utf-8"))
                bundle["history"] = h_data.get("messages", []) if isinstance(h_data, dict) else h_data
            except Exception:
                pass
                
        mem_f = dir_path / "memories.json"
        if mem_f.exists():
            try:
                bundle["memories"] = json.load(open(mem_f, "r", encoding="utf-8"))
            except Exception:
                pass
                
        data_f = dir_path / "databank.json"
        if data_f.exists():
            try:
                bundle["databank"] = json.load(open(data_f, "r", encoding="utf-8"))
            except Exception:
                pass
                
        prof_f = dir_path / "profile.md"
        if prof_f.exists():
            try:
                bundle["profile"] = open(prof_f, "r", encoding="utf-8").read()
            except Exception:
                pass

        meta_f = dir_path / "meta.json"
        if meta_f.exists():
            try:
                bundle["meta"] = json.load(open(meta_f, "r", encoding="utf-8"))
            except Exception:
                pass
                
        char_name = bundle["character"].get("name", save_id.replace("_", " ").title())
        bundle["meta"]["id"] = save_id
        bundle["meta"]["character_name"] = char_name
        bundle["meta"]["name"] = bundle["meta"].get("name") or char_name

        # Auto convert legacy directory to single-file json and delete directory
        try:
            write_save(save_id, bundle)
            shutil.rmtree(dir_path, ignore_errors=True)
        except Exception as conv_err:
            print(f"[read_save] Error migrating {dir_path} to single-file JSON: {conv_err}")

        return bundle

    # 3. Default fresh bundle if missing
    bundle = create_fresh_save_bundle(save_id)
    write_save(save_id, bundle)
    return bundle


def write_save(save_id: str, bundle: dict) -> None:
    """Write complete save bundle atomically to single-file JSON."""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    json_path = SAVES_DIR / f"{save_id}.json"
    
    bundle.setdefault("meta", {})
    bundle["meta"]["id"] = save_id
    bundle["meta"]["updated_at"] = datetime.now().isoformat()
    
    # Keep character info in meta in sync
    char = bundle.get("character", {})
    if char:
        bundle["meta"]["character_name"] = char.get("name", bundle["meta"].get("character_name", "Hero"))
        bundle["meta"]["race"] = char.get("race", "Nord")
        bundle["meta"]["gender"] = char.get("gender", "Male")
        bundle["meta"]["class"] = char.get("class", "Mage")
        bundle["meta"]["level"] = char.get("level", 1)
        bundle["meta"]["gold"] = char.get("gold", 0)
        
    world = bundle.get("world", {})
    if world:
        bundle["meta"]["current_province"] = world.get("current_province", "Cyrodiil")
        bundle["meta"]["current_location"] = world.get("current_location", "Imperial Dungeon")
        bundle["meta"]["quest_stage"] = world.get("quest_stage", 10)
        t_date = world.get("tamrielic_date", {})
        if t_date:
            bundle["meta"]["tamrielic_date"] = f"{t_date.get('day', 1)} {t_date.get('month', 'Morning Star')}, 3E {t_date.get('year', 389)}"

    tmp_path = SAVES_DIR / f"{save_id}.json.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)
    tmp_path.replace(json_path)


def create_fresh_save_bundle(save_id: str, character_name: str = "Eternal Champion", race: str = "Nord", gender: str = "Male", character_class: str = "Mage") -> dict:
    """Create a default bundle for a new character."""
    from engine.character import DEFAULT_SHEET, update_character_identity
    import copy
    import uuid

    sheet = copy.deepcopy(DEFAULT_SHEET)
    sheet = update_character_identity(sheet, name=character_name, race=race, gender=gender, character_class=character_class, reset_vitals=True)
    
    default_world_path = BASE_DIR / "core" / "world" / "world_state.json"
    if default_world_path.exists():
        try:
            with open(default_world_path, "r", encoding="utf-8") as f:
                world_state = json.load(f)
        except Exception:
            world_state = {}
    else:
        world_state = {}
        
    if not world_state:
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

    from core.program_config import get_program_greeting, replace_placeholders
    opening_mes = replace_placeholders(get_program_greeting(), user_name=character_name)
    first_msg_id = f"first_mes_{uuid.uuid4().hex[:12]}"

    history = [
        {
            "id": first_msg_id,
            "role": "program",
            "text": opening_mes,
            "content": opening_mes,
            "timestamp": time.time()
        }
    ]

    profile_content = f"# {character_name.upper()}\n- Race: {race}\n- Class: {character_class}\n- Gender: {gender}\n- Description: A brave adventurer.\n"

    bundle = {
        "meta": {
            "id": save_id,
            "name": f"{character_name} 001",
            "character_name": character_name,
            "race": race,
            "gender": gender,
            "class": character_class,
            "level": 1,
            "gold": sheet.get("gold", 75),
            "current_province": world_state.get("current_province", "Cyrodiil"),
            "current_location": world_state.get("current_location", "Imperial Dungeon"),
            "quest_stage": world_state.get("quest_stage", 10),
            "tamrielic_date": "1 Morning Star, 3E 389",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        "character": sheet,
        "world": world_state,
        "history": history,
        "memories": [],
        "databank": [],
        "profile": profile_content
    }
    return bundle


def save_game(character_name: str = None, save_id: str = None) -> dict:
    """Save the active state as the next sequential playername_001.json file."""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    current_bundle = read_save(get_active_save_id())
    
    char = current_bundle.get("character", {})
    raw_name = character_name or char.get("name") or current_bundle.get("meta", {}).get("character_name") or "hero"
    
    # Strip existing numeric suffixes (e.g., ' 001', ' 003', '_001') to prevent compounding names
    base_char_name = re.sub(r'[\s_]+\d{3,}$', '', raw_name).strip()
    if not base_char_name:
        base_char_name = "Hero"
        
    clean_prefix = _get_clean_name(base_char_name)

    if not save_id:
        max_idx = 0
        pattern = re.compile(rf"^{re.escape(clean_prefix)}_(\d{{3,}})$", re.IGNORECASE)
        
        for item in SAVES_DIR.glob("*.json"):
            match = pattern.match(item.stem)
            if match:
                try:
                    idx = int(match.group(1))
                    if idx > max_idx:
                        max_idx = idx
                except ValueError:
                    pass
                    
        next_idx = max_idx + 1
        save_id = f"{clean_prefix}_{next_idx:03d}"
        display_name = f"{base_char_name} {next_idx:03d}"
    else:
        display_name = save_id.replace("_", " ").title()

    current_bundle.setdefault("meta", {})
    current_bundle["meta"]["id"] = save_id
    current_bundle["meta"]["name"] = display_name
    current_bundle["meta"]["character_name"] = base_char_name
    if char:
        char["name"] = base_char_name
    current_bundle["meta"]["updated_at"] = datetime.now().isoformat()
    if "created_at" not in current_bundle["meta"]:
        current_bundle["meta"]["created_at"] = datetime.now().isoformat()

    write_save(save_id, current_bundle)
    set_active_save_id(save_id)
    
    from utils.program import set_active_user
    set_active_user(save_id)
    
    meta = current_bundle["meta"]
    meta["is_active"] = True
    return meta


def create_save(name: str = None, character_name: str = "Eternal Champion", race: str = "Nord", gender: str = "Male", character_class: str = "Mage", user_profile_id: str = None, save_id: str = None) -> dict:
    """Create a new character and write playername_001.json."""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    clean_prefix = _get_clean_name(character_name)
    
    if not save_id:
        save_id = f"{clean_prefix}_001"
        
    bundle = create_fresh_save_bundle(
        save_id=save_id,
        character_name=character_name,
        race=race,
        gender=gender,
        character_class=character_class
    )
    
    if name:
        bundle["meta"]["name"] = name

    write_save(save_id, bundle)
    set_active_save_id(save_id)
    
    from utils.program import set_active_user
    set_active_user(save_id)
    
    meta = bundle["meta"]
    meta["is_active"] = True
    return meta


def load_save(save_id: str) -> dict:
    """Activate a save state by ID."""
    bundle = read_save(save_id)
    set_active_save_id(save_id)
    
    from utils.program import set_active_user
    set_active_user(save_id)
    
    meta = bundle.get("meta", {})
    meta["is_active"] = True
    return meta


def list_saves() -> list:
    """Return sorted list of all save metadata objects."""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    active_id = get_active_save_id()
    saves = []
    seen_ids = set()

    # 1. Inspect single-file JSON saves
    for item in SAVES_DIR.glob("*.json"):
        if item.name.startswith("."):
            continue
        save_id = item.stem
        seen_ids.add(save_id)
        try:
            with open(item, "r", encoding="utf-8") as f:
                data = json.load(f)
                meta = data.get("meta", {})
                if not meta:
                    char = data.get("character", {})
                    meta = {
                        "id": save_id,
                        "name": save_id.replace("_", " ").title(),
                        "character_name": char.get("name", "Hero"),
                        "race": char.get("race", "Nord"),
                        "class": char.get("class", "Mage"),
                        "level": char.get("level", 1),
                        "updated_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    }
                meta["id"] = save_id
                meta["is_active"] = (save_id == active_id)
                saves.append(meta)
        except Exception as e:
            print(f"[list_saves] Error reading {item}: {e}")

    # 2. Inspect legacy directory saves
    for item in SAVES_DIR.iterdir():
        if item.is_dir() and item.name not in seen_ids:
            save_id = item.name
            bundle = read_save(save_id)
            meta = bundle.get("meta", {})
            meta["id"] = save_id
            meta["is_active"] = (save_id == active_id)
            saves.append(meta)

    # Sort with active save first, then latest updated
    saves.sort(key=lambda s: (not s.get("is_active", False), s.get("updated_at", "")), reverse=False)
    return saves


def delete_save(save_id: str, force_delete: bool = True) -> bool:
    """Delete a single save JSON file or directory."""
    json_path = SAVES_DIR / f"{save_id}.json"
    dir_path = SAVES_DIR / save_id
    deleted = False

    if json_path.exists():
        json_path.unlink()
        deleted = True
        
    if dir_path.is_dir():
        shutil.rmtree(dir_path, ignore_errors=True)
        deleted = True

    if not deleted:
        return False

    # If the active save was deleted, switch to the latest remaining save
    if get_active_save_id() == save_id:
        remaining = list_saves()
        if remaining:
            set_active_save_id(remaining[0]["id"])
        else:
            create_save(save_id="eternal_champion_001")
            
    return True
