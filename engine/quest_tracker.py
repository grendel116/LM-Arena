import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def load_quest_stages() -> list:
    """Loads and returns the quest stages list from JSON."""
    path = BASE_DIR / "core" / "world" / "quest_stages.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_current_stage(stage_number: int, stages: list) -> dict:
    """Returns the stage dict for the given stage number."""
    for s in stages:
        if s.get("stage") == stage_number:
            return s
    return {}

def get_stage_context_injection(state: dict, stages: list) -> str:
    """Returns the context_injection string for the current quest stage."""
    stage_num = state.get("quest_stage", 0)
    stage = get_current_stage(stage_num, stages)
    return stage.get("context_injection", "")

def check_stage_conditions(state: dict, stage: dict) -> bool:
    """Checks all conditions in stage['conditions'] against state['world_flags']."""
    flags = state.get("world_flags", {})
    conditions = stage.get("conditions", {})
    for k, v in conditions.items():
        if flags.get(k) != v:
            return False
    return True

def advance_stage(state: dict, stages: list) -> tuple[dict, list]:
    """Advances the quest stage if conditions are met and executes on_complete actions."""
    stage_num = state.get("quest_stage", 0)
    stage = get_current_stage(stage_num, stages)
    
    fired_actions = []
    
    if stage and check_stage_conditions(state, stage):
        for action in stage.get("on_complete", []):
            state = execute_action(state, action)
            fired_actions.append(action)
        state["quest_stage"] = stage_num + 1
        
    return state, fired_actions

def execute_action(state: dict, action: dict) -> dict:
    """Executes a single on_complete action."""
    action_type = action.get("type")
    
    if "world_flags" not in state:
        state["world_flags"] = {}
        
    if action_type == "advance_stage":
        state["quest_stage"] = action.get("next")
    elif action_type == "set_flag":
        state["world_flags"][action.get("flag")] = action.get("value")
    elif action_type == "trigger_vision":
        state["world_flags"][f"vision_{action.get('vision_id')}_pending"] = True
    elif action_type == "unlock_province_travel":
        state["world_flags"]["province_travel_unlocked"] = True
    elif action_type == "add_fragment":
        if "fragments_collected" not in state:
            state["fragments_collected"] = []
        state["fragments_collected"].append(action.get("fragment_id"))
    elif action_type == "unlock_location":
        loc_type = action.get("location_type")
        loc_name = action.get("location_name")
        if loc_type == "city":
            if "cities_discovered" not in state:
                state["cities_discovered"] = []
            if loc_name not in state["cities_discovered"]:
                state["cities_discovered"].append(loc_name)
        elif loc_type == "dungeon":
            if "dungeons_cleared" not in state:
                state["dungeons_cleared"] = []
            if loc_name not in state["dungeons_cleared"]:
                state["dungeons_cleared"].append(loc_name)
    elif action_type == "trigger_npc_event":
        state["world_flags"][f"npc_event_{action.get('npc')}_{action.get('event')}_pending"] = True
        
    return state
