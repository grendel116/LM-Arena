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
    """Loads the world state JSON for the given character."""
    path = _get_save_path(character_name)
    if not path.exists():
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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_world_state(character_name: str, state: dict) -> None:
    """Saves the world state dict to JSON."""
    path = _get_save_path(character_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

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
