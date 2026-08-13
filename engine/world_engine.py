import json
import os
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def _get_save_path(character_name: str) -> Path:
    return BASE_DIR / "variables" / "saves" / character_name / "world_state.json"

def load_world_state(character_name: str) -> dict:
    """Loads the world state JSON for the given character."""
    path = _get_save_path(character_name)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_world_state(character_name: str, state: dict) -> None:
    """Saves the world state dict to JSON."""
    path = _get_save_path(character_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

def get_location_context(state: dict, provinces_data: list, cities_data: list, dungeons_data: list) -> str:
    """Builds a context string for the LLM describing the current location."""
    current_province = state.get("current_province", "Unknown")
    current_location = state.get("current_location", "Unknown")
    
    province_climate = "unknown"
    for p in provinces_data:
        if p.get("name") == current_province:
            province_climate = p.get("climate", "unknown")
            break
            
    dominant_culture = "Unknown"
    for c in cities_data:
        if c.get("name") == current_location:
            dominant_culture = c.get("culture", "Unknown")
            break
            
    date = state.get("date", {"day": 1, "month": "Morning Star", "year": 389})
    
    return (
        f"Current Location: {current_location}, {current_province}\n"
        f"Province Climate: {province_climate}\n"
        f"Dominant Culture: {dominant_culture}\n"
        f"Local Weather: {state.get('weather', 'clear')}\n"
        f"Tamrielic Date: {date.get('day')} {date.get('month')}, Third Era {date.get('year')}"
    )

def travel(state: dict, destination_province: str, destination_city: str) -> dict:
    """Updates state to reflect travel to a new location and advances time."""
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
        
    hours = random.randint(24, 120)
    state = advance_time(state, hours)
    
    encounter_chance = random.random()
    
    return state, {
        "hours_traveled": hours,
        "encounter_chance": encounter_chance,
        "new_province": destination_province,
        "new_location": destination_city
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
