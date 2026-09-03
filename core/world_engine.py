import json
import os
import random
import math
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def load_world_state(save_id: str = None) -> dict:
    """Loads the world state for the active save slot."""
    try:
        from core.save_manager import get_active_save_id, read_save
        slot = save_id or get_active_save_id()
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
            save_world_state(state, slot)
            return state
        except Exception:
            pass
    return {"quest_stage": 10, "current_province": "Cyrodiil", "current_location": "Imperial Dungeon"}


def save_world_state(arg1=None, arg2=None) -> None:
    """Saves the world state dict to the active save file."""
    try:
        from core.save_manager import get_active_save_id, read_save, write_save
        if isinstance(arg1, dict):
            state = arg1
            slot = arg2 or get_active_save_id()
        else:
            slot = arg1 or get_active_save_id()
            state = arg2 or {}

        bundle = read_save(slot)
        bundle["world"] = state
        write_save(slot, bundle)
    except Exception as e:
        print(f"[save_world_state] Error persisting world state: {e}")

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

CANONICAL_ANCHOR_LOCATIONS = {
    "Cyrodiil": {
        "Imperial City": {"pinX": 565.0, "pinY": 368.0, "type": "capital"},
        "Imperial Dungeon": {"pinX": 565.0, "pinY": 368.0, "type": "dungeon"},
        "Chorrol": {"pinX": 465.0, "pinY": 310.0, "type": "city"},
        "Bruma": {"pinX": 545.0, "pinY": 268.0, "type": "city"},
        "Cheydinhal": {"pinX": 648.0, "pinY": 325.0, "type": "city"},
        "Skingrad": {"pinX": 455.0, "pinY": 415.0, "type": "city"},
        "Anvil": {"pinX": 358.0, "pinY": 425.0, "type": "city"},
        "Bravil": {"pinX": 590.0, "pinY": 455.0, "type": "city"},
        "Leyawiin": {"pinX": 635.0, "pinY": 565.0, "type": "city"},
    },
    "Skyrim": {
        "Solitude": {"pinX": 525.0, "pinY": 95.0, "type": "capital"},
        "Whiterun": {"pinX": 570.0, "pinY": 155.0, "type": "city"},
        "Windhelm": {"pinX": 650.0, "pinY": 140.0, "type": "city"},
        "Riften": {"pinX": 665.0, "pinY": 215.0, "type": "city"},
        "Markarth": {"pinX": 455.0, "pinY": 145.0, "type": "city"},
        "Winterhold": {"pinX": 610.0, "pinY": 100.0, "type": "city"},
        "Dawnstar": {"pinX": 560.0, "pinY": 95.0, "type": "city"},
        "Falkreath": {"pinX": 535.0, "pinY": 195.0, "type": "city"},
        "Labyrinthian": {"pinX": 550.0, "pinY": 135.0, "type": "dungeon"},
    },
    "High Rock": {
        "Daggerfall": {"pinX": 144.0, "pinY": 255.0, "type": "capital"},
        "Wayrest": {"pinX": 255.0, "pinY": 180.0, "type": "city"},
        "Crypt of Hearts": {"pinX": 290.0, "pinY": 140.0, "type": "dungeon"},
    },
    "Hammerfell": {
        "Sentinel": {"pinX": 210.0, "pinY": 275.0, "type": "capital"},
        "Rihad": {"pinX": 275.0, "pinY": 415.0, "type": "city"},
        "Taneth": {"pinX": 345.0, "pinY": 395.0, "type": "city"},
        "Fang Lair": {"pinX": 385.0, "pinY": 230.0, "type": "dungeon"},
    },
    "Morrowind": {
        "Mournhold": {"pinX": 835.0, "pinY": 360.0, "type": "capital"},
        "Vivec": {"pinX": 810.0, "pinY": 340.0, "type": "city"},
        "Balmora": {"pinX": 795.0, "pinY": 305.0, "type": "city"},
        "Dagoth Ur": {"pinX": 805.0, "pinY": 260.0, "type": "dungeon"},
    },
    "Valenwood": {
        "Falinesti": {"pinX": 420.0, "pinY": 530.0, "type": "capital"},
        "Silvenar": {"pinX": 410.0, "pinY": 570.0, "type": "city"},
        "Haven": {"pinX": 450.0, "pinY": 645.0, "type": "city"},
        "Woodhearth": {"pinX": 335.0, "pinY": 565.0, "type": "city"},
        "Elden Grove": {"pinX": 445.0, "pinY": 615.0, "type": "dungeon"},
    },
    "Elsweyr": {
        "Torval": {"pinX": 550.0, "pinY": 600.0, "type": "capital"},
        "Corinthe": {"pinX": 575.0, "pinY": 625.0, "type": "city"},
        "Rimmen": {"pinX": 615.0, "pinY": 550.0, "type": "city"},
        "Dune": {"pinX": 505.0, "pinY": 580.0, "type": "city"},
        "Halls of Colossus": {"pinX": 580.0, "pinY": 630.0, "type": "dungeon"},
    },
    "Summerset Isle": {
        "Alinor": {"pinX": 150.0, "pinY": 615.0, "type": "capital"},
        "Cloudrest": {"pinX": 180.0, "pinY": 540.0, "type": "city"},
        "Lillandril": {"pinX": 100.0, "pinY": 575.0, "type": "city"},
        "Crystal Tower": {"pinX": 170.0, "pinY": 560.0, "type": "dungeon"},
    },
    "Black Marsh": {
        "Stormhold": {"pinX": 770.0, "pinY": 520.0, "type": "capital"},
        "Gideon": {"pinX": 730.0, "pinY": 560.0, "type": "city"},
        "Soulrest": {"pinX": 740.0, "pinY": 660.0, "type": "city"},
        "Murkwood": {"pinX": 810.0, "pinY": 610.0, "type": "dungeon"},
    }
}

def procedural_hash(s: str) -> int:
    """32-bit FNV-1a hash for deterministic procedural positioning."""
    h = 2166136261
    for b in s.strip().lower().encode("utf-8"):
        h = (h ^ b) * 16777619 & 0xFFFFFFFF
    return h

def resolve_location_anchor(province_name: str, location_name: str, known_city: str = None) -> dict:
    """
    Procedurally translates any narrative location to its nearest canonical base anchor
    (city or dungeon) using deterministic mathematical offsets and cardinal orientation.
    """
    prov = province_name or "Cyrodiil"
    anchors = CANONICAL_ANCHOR_LOCATIONS.get(prov, CANONICAL_ANCHOR_LOCATIONS["Cyrodiil"])
    loc_clean = (location_name or "Imperial Dungeon").strip()
    loc_lower = loc_clean.lower()
    
    # 1. Direct match with a canonical base location
    for name, data in anchors.items():
        if loc_lower == name.lower():
            return {
                "location_name": loc_clean,
                "anchor_name": name,
                "anchor_type": data["type"],
                "coords": {"pinX": data["pinX"], "pinY": data["pinY"]},
                "orientation": name,
                "narrative_orientation": f"within {name}"
            }
            
    # 2. Determine nearest canonical base anchor
    anchor_name = None
    for name in anchors:
        if name.lower() in loc_lower:
            anchor_name = name
            break
            
    if not anchor_name and known_city and known_city in anchors:
        anchor_name = known_city
        
    if not anchor_name:
        # Default to the province's primary anchor/capital
        anchor_name = list(anchors.keys())[0]

    anchor_data = anchors[anchor_name]

    # 3. Procedural mathematical offset using deterministic trigonometry
    h = procedural_hash(loc_clean)
    angle_rad = math.radians(h % 360)
    radius = 22.0 + (h % 18)
    dx = round(radius * math.cos(angle_rad), 1)
    dy = round(radius * math.sin(angle_rad), 1)

    deg = (math.degrees(math.atan2(dy, dx)) + 360) % 360
    directions = ["east", "southeast", "south", "southwest", "west", "northwest", "north", "northeast"]
    direction = directions[int((deg + 22.5) // 45) % 8]

    return {
        "location_name": loc_clean,
        "anchor_name": anchor_name,
        "anchor_type": anchor_data["type"],
        "coords": {"pinX": anchor_data["pinX"] + dx, "pinY": anchor_data["pinY"] + dy},
        "orientation": f"{loc_clean} (near {anchor_name})",
        "narrative_orientation": f"in the wilderness {direction} of {anchor_name}"
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
            
    date = state.get("tamrielic_date") or state.get("date") or {"day": 1, "month": "Hearthfire", "year": 389}
    
    geo = TAMRIEL_GEOGRAPHY.get(current_province, {
        "region": "Tamriel Realm",
        "borders": "Adjacent Provinces",
        "routes": "Roads and trails"
    })

    loc_info = resolve_location_anchor(current_province, current_location)
    
    return (
        f"Current Location: {loc_info['orientation']}, {current_province}\n"
        f"Regional Orientation: Currently situated {loc_info['narrative_orientation']}.\n"
        f"Nearest Major Landmark/Hub: {loc_info['anchor_name']} ({loc_info['anchor_type'].capitalize()})\n"
        f"Geographic Region: {geo['region']}\n"
        f"Bordering Lands: {geo['borders']}\n"
        f"Major Travel Routes: {geo['routes']}\n"
        f"Province Climate: {province_climate}\n"
        f"Dominant Culture: {dominant_culture}\n"
        f"Local Weather: {state.get('weather', 'clear')}\n"
        f"Tamrielic Date: {date.get('day', 1)} {date.get('month', 'Hearthfire')}, Third Era {date.get('year', 389)}"
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

# Canonical 12 Tamrielic Months (each 30 days, 360-day calendar year)
TAMRIELIC_MONTHS = [
    "Morning Star", "Sun's Dawn", "First Seed", "Rain's Hand",
    "Second Seed", "Midyear", "Sun's Height", "Last Seed",
    "Hearthfire", "Frostfall", "Sun's Dusk", "Evening Star"
]

CANONICAL_HOLIDAYS = {
    (1, "Morning Star"): "New Life Festival",
    (2, "Morning Star"): "Scour Day",
    (16, "Sun's Dawn"): "Heart's Day",
    (7, "First Seed"): "First Planting",
    (28, "Rain's Hand"): "Jester's Day",
    (7, "Second Seed"): "Second Planting",
    (16, "Midyear"): "Midyear Celebration",
    (10, "Sun's Height"): "Merchant's Festival",
    (27, "Last Seed"): "Harvest's End",
    (3, "Hearthfire"): "Tales and Tallows",
    (13, "Frostfall"): "Witches' Festival",
    (20, "Sun's Dusk"): "South Wall's Day",
    (15, "Evening Star"): "North Wind's Prayer",
    (18, "Evening Star"): "Baranth Do",
    (30, "Evening Star"): "Old Life Festival"
}

def get_time_of_day_label(hour: int) -> str:
    """Returns the canonical 7-bracket time of day name from Arena."""
    h = hour % 24
    if 0 <= h < 3:
        return "Midnight"
    elif 3 <= h < 6:
        return "Night"
    elif 6 <= h < 9:
        return "Early Morning"
    elif 9 <= h < 12:
        return "Morning"
    elif 12 <= h < 18:
        return "Afternoon"
    elif 18 <= h < 21:
        return "Evening"
    else:
        return "Late Evening"

def get_holiday(day: int, month: str) -> str | None:
    """Returns holiday name if the date matches a canonical Tamrielic festival."""
    return CANONICAL_HOLIDAYS.get((day, month))

def generate_weather(province: str = "Cyrodiil", month: str = "Hearthfire") -> str:
    """Generates authentic regional Tamrielic weather based on province climate and season."""
    prov = (province or "Cyrodiil").lower()
    m = (month or "Hearthfire").lower()
    is_winter = m in ["frostfall", "sun's dusk", "evening star", "morning star", "sun's dawn"]
    is_summer = m in ["second seed", "midyear", "sun's height", "last seed"]
    
    if "skyrim" in prov:
        if is_winter:
            return random.choices(["Blizzard", "Heavy Snowfall", "Freezing Mist", "Overcast Snow", "Clear and Frigid"], weights=[25, 35, 15, 15, 10])[0]
        else:
            return random.choices(["Chilly Rain", "Overcast", "Clear Skies", "Mountain Fog", "Light Flurries"], weights=[25, 30, 25, 15, 5])[0]
    elif "hammerfell" in prov or "elsweyr" in prov:
        if is_summer:
            return random.choices(["Blazing Sun", "Heatwave", "Dust Storm", "Clear Skies", "Dry Winds"], weights=[40, 25, 15, 15, 5])[0]
        else:
            return random.choices(["Clear Skies", "Cool Desert Breeze", "Overcast", "Sudden Flash Rain"], weights=[50, 30, 15, 5])[0]
    elif "black marsh" in prov or "valenwood" in prov:
        if is_summer:
            return random.choices(["Tropical Downpour", "Humid Thunderstorm", "Dense Fog", "Warm Drizzle", "Muggy Overcast"], weights=[30, 25, 20, 15, 10])[0]
        else:
            return random.choices(["Swamp Mist", "Steady Rain", "Overcast", "Clearing Skies"], weights=[35, 30, 25, 10])[0]
    elif "morrowind" in prov:
        return random.choices(["Ash Haze", "Overcast", "Acidic Rain", "Clear Skies", "Sulfur Fog"], weights=[30, 25, 20, 15, 10])[0]
    elif "high rock" in prov:
        if is_winter:
            return random.choices(["Cold Rain", "Sleet", "Overcast", "Coastal Fog", "Snow Flurries"], weights=[30, 25, 20, 15, 10])[0]
        else:
            return random.choices(["Coastal Fog", "Gentle Rain", "Clear Skies", "Overcast"], weights=[35, 25, 25, 15])[0]
    else:  # Cyrodiil & Summerset Isle (Temperate / Island)
        if is_winter:
            return random.choices(["Cold Drizzle", "Overcast", "Crisp Clear Skies", "Morning Frost Fog"], weights=[35, 30, 20, 15])[0]
        elif is_summer:
            return random.choices(["Warm Clear Skies", "Gentle Breeze", "Summer Thunderstorm", "Scattered Clouds"], weights=[45, 25, 15, 15])[0]
        else:
            return random.choices(["Overcast", "Passing Rain", "Clear Skies", "Autumn Mist"], weights=[35, 30, 25, 10])[0]

def advance_time(state: dict, hours: int) -> dict:
    """Advances the canonical Tamrielic calendar (30 days/month, 12 months/year) and updates weather."""
    if "date" not in state:
        state["date"] = {"day": 1, "month": "Hearthfire", "year": 389, "hour": 6}
        
    date = state["date"]
    date["hour"] = date.get("hour", 6) + hours
    
    days_to_add = date["hour"] // 24
    date["hour"] %= 24
    
    date["day"] = date.get("day", 1) + days_to_add
    
    current_month_idx = 0
    if date.get("month") in TAMRIELIC_MONTHS:
        current_month_idx = TAMRIELIC_MONTHS.index(date["month"])
        
    while date["day"] > 30:
        date["day"] -= 30
        current_month_idx += 1
        if current_month_idx >= 12:
            current_month_idx = 0
            date["year"] = date.get("year", 389) + 1
            
    date["month"] = TAMRIELIC_MONTHS[current_month_idx]
    
    # Update dynamic weather if hours progressed significantly
    if hours >= 4 or "weather" not in state:
        state["weather"] = generate_weather(state.get("current_province", "Cyrodiil"), date["month"])
        
    return state

def set_flag(state: dict, flag_name: str, value) -> dict:
    """Sets a flag in state['world_flags']."""
    if "world_flags" not in state:
        state["world_flags"] = {}
    state["world_flags"][flag_name] = value
    return state

def set_location(arg1: str, arg2: str = None, arg3: str = None, advance_hours: int = 0, **kwargs) -> dict:
    """Sets the character's active location and province directly, discovering them in world state."""
    if arg3 is not None:
        province = arg2
        location_name = arg3
    elif arg2 is not None:
        province = arg1
        location_name = arg2
    else:
        province = "Cyrodiil"
        location_name = arg1

    world_state = load_world_state()
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

    adv = advance_hours if isinstance(advance_hours, int) else 0
    if adv > 0:
        world_state = advance_time(world_state, adv)

    save_world_state(world_state)
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
    date = world_state.get("date") or world_state.get("tamrielic_date") or {"day": 1, "month": "Hearthfire", "year": 389, "hour": 6}
    derived = (character_sheet or {}).get("derived", {})
    inventory = copy.deepcopy((character_sheet or {}).get("inventory", []))
    spells = copy.deepcopy((character_sheet or {}).get("spells", []))
    return {
        "province": world_state.get("current_province", "Cyrodiil"),
        "location": world_state.get("current_location", "Imperial Dungeon"),
        "date": {
            "day": date.get("day", 1),
            "month": date.get("month", "Hearthfire"),
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
    if "bgm" in snapshot:
        world_state["bgm"] = snapshot["bgm"]
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
        from core.character import load_character, save_character
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
            elif key in ("bgm", "music", "track"):
                snapshot["bgm"] = str(val).strip()
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



