import json
import os
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def _normalize_save_slot(character_name: str) -> str:
    if not character_name or str(character_name).strip() in ("{{user}}", "user", "player", "current", ""):
        try:
            from engine.save_manager import get_active_save_id
            return get_active_save_id()
        except Exception:
            return "eternal_champion"
    return str(character_name).strip().lower().replace(" ", "_").replace("-", "_")

def _get_save_path(character_name: str) -> Path:
    slot = _normalize_save_slot(character_name)
    return BASE_DIR / "variables" / "saves" / slot / "world_state.json"

def load_world_state(character_name: str) -> dict:
    """Loads the world state for the active save slot."""
    slot = _normalize_save_slot(character_name)
    try:
        from engine.save_manager import read_save
        bundle = read_save(slot)
        state = bundle.get("world", {})
        if state:
            return state
    except Exception:
        pass

    default_world_path = BASE_DIR / "core" / "world" / "world_state.json"
    if default_world_path.exists():
        try:
            with open(default_world_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            save_world_state(character_name, state)
            return state
        except Exception:
            pass
    return {"quest_stage": 10, "current_province": "Cyrodiil", "current_location": "Imperial Dungeon"}

def save_world_state(character_name: str, state: dict) -> None:
    """Saves the world state dict to the save file."""
    slot = _normalize_save_slot(character_name)
    try:
        from engine.save_manager import read_save, write_save
        bundle = read_save(slot)
        bundle["world"] = state
        write_save(slot, bundle)
    except Exception as e:
        print(f"[save_world_state] Error persisting world state to {slot}: {e}")

TAMRIEL_GEOGRAPHY = {
    "High Rock": {
        "region": "Northwest Tamriel",
        "borders": "Skyrim (East), Hammerfell (South across Dragontail Mountains / Iliac Bay), Abecean Sea (West)",
        "routes": "Mountain passes east into Skyrim, coastal and desert roads south into Hammerfell."
    },
    "Hammerfell": {
        "region": "West Tamriel",
        "borders": "High Rock (North), Skyrim (Northeast), Cyrodiil (East across Colovian Highlands), Abecean Sea (West & South)",
        "routes": "Mountain passes northeast into Skyrim, high road east into Cyrodiil, northern roads into High Rock."
    },
    "Skyrim": {
        "region": "North Tamriel",
        "borders": "High Rock (West), Hammerfell (Southwest), Cyrodiil (South across Jerall Mountains / Pale Pass), Morrowind (East across Velothi Mountains)",
        "routes": "Pale Pass south into Cyrodiil, Dunmeth Pass east into Morrowind, western passes into High Rock & Hammerfell."
    },
    "Morrowind": {
        "region": "Northeast Tamriel",
        "borders": "Skyrim (West across Velothi Mountains), Cyrodiil (Southwest across Valus Mountains), Black Marsh (South)",
        "routes": "Dunmeth Pass west into Skyrim, Cheydinhal Pass southwest into Cyrodiil, southern border roads into Black Marsh."
    },
    "Cyrodiil": {
        "region": "Central Heartland of Tamriel",
        "borders": "Skyrim (North), Hammerfell (Northwest), High Rock (Far Northwest), Valenwood (Southwest), Elsweyr (South), Black Marsh (Southeast), Morrowind (Northeast)",
        "routes": "Hub of the Empire with imperial highways radiating north to Skyrim, west to Hammerfell, south to Elsweyr/Valenwood, and east to Morrowind/Black Marsh."
    },
    "Summerset Isle": {
        "region": "Southwest Archipelago",
        "borders": "Surrounded by the Abecean Sea and Sea of Pearls; closest mainland ports in Valenwood and Hammerfell",
        "routes": "Requires sea voyage to/from ports in Valenwood (Woodhearth), Hammerfell (Rihad/Stros M'kai), or Cyrodiil (Anvil)."
    },
    "Valenwood": {
        "region": "Southwest Tamriel",
        "borders": "Cyrodiil (Northeast), Elsweyr (East), Abecean Sea (West & South)",
        "routes": "Green Road northeast into Cyrodiil, river crossings and jungle trails east into Elsweyr."
    },
    "Elsweyr": {
        "region": "South Tamriel",
        "borders": "Cyrodiil (North), Valenwood (West), Black Marsh (East across Topal Bay), Southern Ocean (South)",
        "routes": "Imperial roads north into Cyrodiil, river crossings west into Valenwood, coastal trade ships to Black Marsh."
    },
    "Black Marsh": {
        "region": "Southeast Tamriel",
        "borders": "Morrowind (North), Cyrodiil (West), Topal Bay / Elsweyr (Southwest), Padomaic Ocean (East)",
        "routes": "Imperial road west through Leyawiin/Gideon into Cyrodiil, northern swamp roads into Morrowind."
    }
}

def get_location_context(state: dict, provinces_data: list, cities_data: list, dungeons_data: list) -> str:
    """Builds a rich geographic and environmental context string for the LLM DM."""
    current_province = state.get("current_province", "Cyrodiil")
    current_location = state.get("current_location", "Imperial Dungeon")
    
    province_climate = "temperate"
    for p in provinces_data:
        if p.get("name", "").lower() == current_province.lower():
            province_climate = p.get("climate", "temperate")
            break
            
    dominant_culture = "Imperial"
    for c in cities_data:
        if c.get("name", "").lower() == current_location.lower():
            dominant_culture = c.get("culture", "Imperial")
            break
            
    date = state.get("tamrielic_date") or state.get("date") or {"day": 1, "month": "Morning Star", "year": 389}
    
    geo = TAMRIEL_GEOGRAPHY.get(current_province, {
        "region": "Tamriel Realm",
        "borders": "Adjacent Provinces",
        "routes": "Roads and trails"
    })
    
    return (
        f"Current Location: {current_location}, {current_province}\n"
        f"Geographic Region: {geo['region']}\n"
        f"Bordering Lands: {geo['borders']}\n"
        f"Major Travel Routes: {geo['routes']}\n"
        f"Province Climate: {province_climate}\n"
        f"Dominant Culture: {dominant_culture}\n"
        f"Local Weather: {state.get('weather', 'clear')}\n"
        f"Tamrielic Date: {date.get('day', 1)} {date.get('month', 'Morning Star')}, Third Era {date.get('year', 389)}"
    )

def travel(state: dict, destination_province: str, destination_city: str) -> dict:
    """Updates state to reflect narrative travel to a new location and advances time."""
    prev_province = state.get("current_province", "Cyrodiil")
    state["current_province"] = destination_province
    state["current_location"] = destination_city
    
    if "provinces_visited" not in state:
        state["provinces_visited"] = []
    if destination_province not in state["provinces_visited"]:
        state["provinces_visited"].append(destination_province)
        
    if "cities_discovered" not in state:
        state["cities_discovered"] = []
    if destination_city not in state["cities_discovered"]:
        state["cities_discovered"].append(destination_city)
        
    # Approximate travel time based on adjacency
    hours = random.randint(24, 48) if destination_province == prev_province else random.randint(72, 144)
    state = advance_time(state, hours)
    
    encounter_chance = random.random()
    
    dest_geo = TAMRIEL_GEOGRAPHY.get(destination_province, {})
    
    return state, {
        "hours_traveled": hours,
        "encounter_chance": encounter_chance,
        "prev_province": prev_province,
        "new_province": destination_province,
        "new_location": destination_city,
        "destination_region": dest_geo.get("region", "Tamriel")
    }

def advance_time(state: dict, hours: int) -> dict:
    """Advances the Tamrielic calendar by the given hours."""
    months = [
        ("Morning Star", 31), ("Sun's Dawn", 28), ("First Seed", 31),
        ("Rain's Hand", 30), ("Second Seed", 31), ("Midyear", 30),
        ("Sun's Height", 31), ("Last Seed", 31), ("Hearthfire", 30),
        ("Frostfall", 31), ("Sun's Dusk", 30), ("Evening Star", 31)
    ]
    
    if "date" not in state:
        state["date"] = {"day": 1, "month": "Morning Star", "year": 389, "hour": 0}
        
    date = state["date"]
    date["hour"] = date.get("hour", 0) + hours
    
    days_to_add = date["hour"] // 24
    date["hour"] %= 24
    
    date["day"] = date.get("day", 1) + days_to_add
    
    current_month_idx = 0
    for i, (m, d) in enumerate(months):
        if m == date["month"]:
            current_month_idx = i
            break
            
    while True:
        days_in_month = months[current_month_idx][1]
        if date["day"] <= days_in_month:
            break
        date["day"] -= days_in_month
        current_month_idx += 1
        if current_month_idx >= 12:
            current_month_idx = 0
            date["year"] = date.get("year", 389) + 1
            
    date["month"] = months[current_month_idx][0]
    return state

def set_flag(state: dict, flag_name: str, value) -> dict:
    """Sets a flag in state['world_flags']."""
    if "world_flags" not in state:
        state["world_flags"] = {}
    state["world_flags"][flag_name] = value
    return state

def set_location(character_name: str, province: str, location_name: str, advance_hours: int = 0) -> dict:
    """Sets the character's active location and province directly, discovering them in world state."""
    world_state = load_world_state(character_name)
    prev_province = world_state.get("current_province", "Cyrodiil")
    prev_location = world_state.get("current_location", "Imperial Dungeon")

    world_state["current_province"] = province
    world_state["current_location"] = location_name

    if "provinces_visited" not in world_state:
        world_state["provinces_visited"] = []
    if province not in world_state["provinces_visited"]:
        world_state["provinces_visited"].append(province)

    if "cities_discovered" not in world_state:
        world_state["cities_discovered"] = []
    if location_name not in world_state["cities_discovered"]:
        world_state["cities_discovered"].append(location_name)

    if advance_hours > 0:
        world_state = advance_time(world_state, advance_hours)

    save_world_state(character_name, world_state)
    return {
        "status": "success",
        "previous_province": prev_province,
        "previous_location": prev_location,
        "current_province": province,
        "current_location": location_name,
        "world_state": world_state
    }

def discover_location(state: dict, location_type: str, location_name: str) -> dict:

    """Adds a city or dungeon to the discovered list."""
    if location_type == "city":
        if "cities_discovered" not in state:
            state["cities_discovered"] = []
        if location_name not in state["cities_discovered"]:
            state["cities_discovered"].append(location_name)
    elif location_type == "dungeon":
        if "dungeons_cleared" not in state:
            state["dungeons_cleared"] = []
        if location_name not in state["dungeons_cleared"]:
            state["dungeons_cleared"].append(location_name)
    return state


import copy

def create_state_snapshot(world_state: dict, character_sheet: dict = None) -> dict:
    """Creates a compact snapshot of location, date/time, quest, vitals, inventory, and spells."""
    date = world_state.get("date") or world_state.get("tamrielic_date") or {"day": 1, "month": "Morning Star", "year": 389, "hour": 6}
    derived = (character_sheet or {}).get("derived", {})
    inventory = copy.deepcopy((character_sheet or {}).get("inventory", []))
    spells = copy.deepcopy((character_sheet or {}).get("spells", []))
    return {
        "province": world_state.get("current_province", "Cyrodiil"),
        "location": world_state.get("current_location", "Imperial Dungeon"),
        "date": {
            "day": date.get("day", 1),
            "month": date.get("month", "Morning Star"),
            "year": date.get("year", 389),
            "hour": date.get("hour", 6),
            "era": date.get("era", "Third Era")
        },
        "quest_stage": world_state.get("quest_stage", 10),
        "world_flags": dict(world_state.get("world_flags", {})),
        "vitals": {
            "hp": derived.get("hp_current", 30),
            "hp_max": derived.get("hp_max", 30),
            "mp": derived.get("mp_current", 162),
            "mp_max": derived.get("mp_max", 162),
            "stamina": derived.get("stamina_current", 60),
            "stamina_max": derived.get("stamina_max", 60),
            "gold": (character_sheet or {}).get("gold", 0)
        },
        "inventory": inventory,
        "spells": spells
    }

def apply_state_snapshot(character_name: str, snapshot: dict) -> None:
    """Restores world state, character vitals, inventory, and spells from a snapshot."""
    if not snapshot or not isinstance(snapshot, dict):
        return

    world_state = load_world_state(character_name)
    if "province" in snapshot:
        world_state["current_province"] = snapshot["province"]
    if "location" in snapshot:
        world_state["current_location"] = snapshot["location"]
    if "date" in snapshot:
        world_state["date"] = snapshot["date"]
        world_state["tamrielic_date"] = snapshot["date"]
    if "quest_stage" in snapshot:
        world_state["quest_stage"] = snapshot["quest_stage"]
    if "world_flags" in snapshot:
        world_state["world_flags"] = snapshot["world_flags"]

    if "provinces_visited" not in world_state:
        world_state["provinces_visited"] = []
    p = world_state.get("current_province")
    if p and p not in world_state["provinces_visited"]:
        world_state["provinces_visited"].append(p)

    if "cities_discovered" not in world_state:
        world_state["cities_discovered"] = []
    loc = world_state.get("current_location")
    if loc and loc not in world_state["cities_discovered"]:
        world_state["cities_discovered"].append(loc)

    save_world_state(character_name, world_state)

    try:
        from engine.character import load_character, save_character
        sheet = load_character(character_name)
        char_modified = False
        vitals = snapshot.get("vitals")
        if vitals:
            derived = sheet.setdefault("derived", {})
            if "hp" in vitals:
                derived["hp_current"] = vitals["hp"]
                char_modified = True
            if "hp_max" in vitals:
                derived["hp_max"] = vitals["hp_max"]
                char_modified = True
            if "mp" in vitals:
                derived["mp_current"] = vitals["mp"]
                char_modified = True
            if "mp_max" in vitals:
                derived["mp_max"] = vitals["mp_max"]
                char_modified = True
            if "stamina" in vitals:
                derived["stamina_current"] = vitals["stamina"]
                char_modified = True
            if "stamina_max" in vitals:
                derived["stamina_max"] = vitals["stamina_max"]
                char_modified = True
            if "gold" in vitals:
                sheet["gold"] = vitals["gold"]
                char_modified = True

        if "inventory" in snapshot and isinstance(snapshot["inventory"], list):
            sheet["inventory"] = copy.deepcopy(snapshot["inventory"])
            char_modified = True

        if "spells" in snapshot and isinstance(snapshot["spells"], list):
            sheet["spells"] = copy.deepcopy(snapshot["spells"])
            char_modified = True

        if char_modified:
            save_character(character_name, sheet)
    except Exception as e:
        print(f"[apply_state_snapshot] Error applying character sheet updates: {e}")

def extract_hidden_state_footer(text: str, current_snapshot: dict) -> tuple[str, dict]:
    """Extracts and strips hidden state comments from text, updating the snapshot."""
    if not text:
        return text, current_snapshot

    import re
    snapshot = copy.deepcopy(current_snapshot) if current_snapshot else {}
    pattern = r'<!--\s*state:\s*(.*?)\s*-->'
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        raw_params = match.group(1)
        kv_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,;]+))'
        for kv in re.finditer(kv_pattern, raw_params):
            key = kv.group(1).lower()
            val = kv.group(2) if kv.group(2) is not None else (kv.group(3) if kv.group(3) is not None else kv.group(4))
            if key == "province":
                snapshot["province"] = str(val).strip()
            elif key == "location":
                snapshot["location"] = str(val).strip()
            elif key in ("quest_stage", "stage"):
                try:
                    snapshot["quest_stage"] = int(val)
                except Exception:
                    pass
            elif key == "hour":
                try:
                    snapshot.setdefault("date", {})["hour"] = int(val) % 24
                except Exception:
                    pass
            elif key in ("time", "time_of_day"):
                t_val = str(val).lower().strip()
                t_map = {
                    "dawn": 6, "pre-dawn": 5, "predawn": 5,
                    "morning": 8, "early morning": 6,
                    "noon": 12, "midday": 12, "afternoon": 14,
                    "dusk": 18, "sunset": 18, "evening": 19,
                    "night": 22, "midnight": 0
                }
                if t_val in t_map:
                    snapshot.setdefault("date", {})["hour"] = t_map[t_val]
            elif key in ("hours", "time_advance", "advance_hours"):
                try:
                    hrs = int(val)
                    if "date" in snapshot:
                        temp_state = {"date": snapshot["date"]}
                        temp_state = advance_time(temp_state, hrs)
                        snapshot["date"] = temp_state["date"]
                except Exception:
                    pass

            elif key in ("hp", "hp_current"):
                try:
                    snapshot.setdefault("vitals", {})["hp"] = int(val)
                except Exception:
                    pass
            elif key in ("mp", "mp_current"):
                try:
                    snapshot.setdefault("vitals", {})["mp"] = int(val)
                except Exception:
                    pass
            elif key in ("stamina", "sp"):
                try:
                    snapshot.setdefault("vitals", {})["stamina"] = int(val)
                except Exception:
                    pass
            elif key == "gold":
                try:
                    snapshot.setdefault("vitals", {})["gold"] = int(val)
                except Exception:
                    pass

            elif key in ("add_item", "loot", "give_item"):
                parts = str(val).split(":")
                item_name = parts[0].strip()
                item_type = parts[1].strip() if len(parts) > 1 else "misc"
                qty = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip().isdigit() else 1
                inv = snapshot.setdefault("inventory", [])
                found = False
                for it in inv:
                    if it.get("name", "").lower() == item_name.lower():
                        it["quantity"] = it.get("quantity", 1) + qty
                        found = True
                        break
                if not found:
                    inv.append({"name": item_name, "type": item_type, "quantity": qty})

            elif key in ("remove_item", "drop_item", "consume", "eat", "use_item"):
                parts = str(val).split(":")
                item_name = parts[0].strip()
                qty = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip().isdigit() else 1
                inv = snapshot.setdefault("inventory", [])
                for i, it in enumerate(inv):
                    if it.get("name", "").lower() == item_name.lower():
                        curr_qty = it.get("quantity", 1)
                        if curr_qty > qty:
                            it["quantity"] = curr_qty - qty
                        else:
                            inv.pop(i)
                        break

            elif key in ("learn_spell", "add_spell"):
                parts = str(val).split(":")
                sp_name = parts[0].strip()
                sp_cost = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip().isdigit() else 10
                sp_school = parts[2].strip() if len(parts) > 2 else "Destruction"
                spells = snapshot.setdefault("spells", [])
                if not any(s.get("name", "").lower() == sp_name.lower() for s in spells):
                    spells.append({"name": sp_name, "mp_cost": sp_cost, "school": sp_school})

            elif key in ("remove_spell", "forget_spell"):
                sp_name = str(val).strip()
                spells = snapshot.setdefault("spells", [])
                snapshot["spells"] = [s for s in spells if s.get("name", "").lower() != sp_name.lower()]

        cleaned_text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL).rstrip()
        return cleaned_text, snapshot

    return text, snapshot


def sync_world_state_from_history(character_name: str, history: list) -> dict:
    """Returns the active world state for the character."""
    return load_world_state(character_name)

    # Fallback to walking tool calls in history
    default_world_path = BASE_DIR / "core" / "world" / "world_state.json"
    if default_world_path.exists():
        try:
            with open(default_world_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {"quest_stage": 10, "current_province": "Cyrodiil", "current_location": "Imperial Dungeon"}
    else:
        state = {"quest_stage": 10, "current_province": "Cyrodiil", "current_location": "Imperial Dungeon"}

    stages = load_quest_stages()

    for msg in history:
        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            t_name = tc.get("name", "")
            args = tc.get("args", {})
            if not isinstance(args, dict):
                continue

            if t_name == "arena_set_location":
                prov = args.get("province")
                loc = args.get("location_name")
                if prov:
                    state["current_province"] = prov
                    if "provinces_visited" not in state:
                        state["provinces_visited"] = []
                    if prov not in state["provinces_visited"]:
                        state["provinces_visited"].append(prov)
                if loc:
                    state["current_location"] = loc
                    if "cities_discovered" not in state:
                        state["cities_discovered"] = []
                    if loc not in state["cities_discovered"]:
                        state["cities_discovered"].append(loc)
                adv_hrs = int(args.get("advance_hours", 0)) if args.get("advance_hours") is not None else 0
                if adv_hrs > 0:
                    state = advance_time(state, adv_hrs)

            elif t_name == "arena_travel":
                prov = args.get("destination_province")
                city = args.get("destination_city")
                if prov and city:
                    state, _ = travel(state, prov, city)

            elif t_name == "arena_advance_stage":
                target_stage = args.get("target_stage")
                if target_stage is not None:
                    state["quest_stage"] = int(target_stage)
                else:
                    state, _ = advance_stage(state, stages)

            elif t_name == "arena_set_quest_stage":
                st = args.get("stage_number")
                if st is not None:
                    state["quest_stage"] = int(st)

    save_world_state(character_name, state)
    return state



