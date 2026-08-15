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
    """Returns the stage dict for the given stage number or highest preceding active stage."""
    if not stages:
        return {}
    for s in stages:
        if s.get("stage") == stage_number:
            return s
    active_stage = None
    for s in sorted(stages, key=lambda x: x.get("stage", 0)):
        if s.get("stage", 0) <= stage_number:
            active_stage = s
        else:
            break
    return active_stage or stages[0]


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


def advance_stage(state: dict, stages: list, force: bool = True) -> tuple[dict, list]:
    """Advances the quest stage and executes on_complete actions."""
    stage_num = state.get("quest_stage", 10)
    stage = get_current_stage(stage_num, stages)
    
    fired_actions = []
    
    next_stage_num = stage_num + 10
    if stage:
        for action in stage.get("on_complete", []):
            state = execute_action(state, action)
            fired_actions.append(action)
            act_type = action.get("action") or action.get("type")
            params = action.get("params") or action
            if act_type == "advance_stage":
                if "next_stage" in params:
                    next_stage_num = params["next_stage"]
                elif "next" in params:
                    next_stage_num = params["next"]
                    
        state["quest_stage"] = next_stage_num
    else:
        state["quest_stage"] = next_stage_num
        
    return state, fired_actions

def execute_action(state: dict, action: dict) -> dict:
    """Executes a single on_complete action supporting both schema formats."""
    action_type = action.get("action") or action.get("type")
    params = action.get("params") or action
    
    if "world_flags" not in state:
        state["world_flags"] = {}
        
    if action_type == "advance_stage":
        next_s = params.get("next_stage") or params.get("next")
        if next_s:
            state["quest_stage"] = next_s
    elif action_type == "set_flag":
        state["world_flags"][params.get("flag")] = params.get("value", True)
    elif action_type == "trigger_vision":
        vision_id = params.get("vision_id")
        if vision_id:
            state["world_flags"][f"vision_{vision_id}_pending"] = True
    elif action_type == "unlock_province_travel":
        state["world_flags"]["province_travel_unlocked"] = True
    elif action_type == "add_fragment":
        if "fragments_collected" not in state:
            state["fragments_collected"] = []
        frag = params.get("fragment_id")
        if frag and frag not in state["fragments_collected"]:
            state["fragments_collected"].append(frag)
    elif action_type == "unlock_location":
        loc_id = params.get("location_id") or params.get("location_name")
        loc_type = params.get("location_type", "dungeon")
        if loc_type == "city":
            if "cities_discovered" not in state:
                state["cities_discovered"] = []
            if loc_id and loc_id not in state["cities_discovered"]:
                state["cities_discovered"].append(loc_id)
        elif loc_type == "dungeon":
            if "dungeons_cleared" not in state:
                state["dungeons_cleared"] = []
            if loc_id and loc_id not in state["dungeons_cleared"]:
                state["dungeons_cleared"].append(loc_id)
    elif action_type == "trigger_npc_event":
        npc = params.get("npc")
        event = params.get("event")
        if npc and event:
            state["world_flags"][f"npc_event_{npc}_{event}_pending"] = True
        
    return state

def advance_quest_stage(character_name: str, target_stage: int = None) -> dict:
    """Advances the active character's quest stage and saves the world state."""
    from engine.world_engine import load_world_state, save_world_state
    world_state = load_world_state(character_name)
    current_stage_num = world_state.get("quest_stage", 10)
    stages = load_quest_stages()

    if target_stage is not None:
        new_stage_num = int(target_stage)
        stage = get_current_stage(current_stage_num, stages)
        fired_actions = []
        if stage:
            for action in stage.get("on_complete", []):
                world_state = execute_action(world_state, action)
                fired_actions.append(action)
        world_state["quest_stage"] = new_stage_num
    else:
        world_state, fired_actions = advance_stage(world_state, stages)
        new_stage_num = world_state.get("quest_stage", current_stage_num + 10)

    save_world_state(character_name, world_state)
    new_stage = get_current_stage(new_stage_num, stages)
    
    return {
        "status": "success",
        "previous_stage": current_stage_num,
        "current_stage": new_stage_num,
        "stage_label": new_stage.get("label", f"Stage {new_stage_num}"),
        "objectives": new_stage.get("objectives", []),
        "fired_actions": fired_actions
    }

def set_quest_stage(character_name: str, stage_number: int) -> dict:
    """Sets the character's quest stage directly."""
    return advance_quest_stage(character_name, target_stage=int(stage_number))

def sync_quest_stage_with_location(character_name: str) -> dict:
    """Auto-advances quest stage if the player has moved past earlier milestones in the narrative."""
    from engine.world_engine import load_world_state, save_world_state
    state = load_world_state(character_name)
    loc = str(state.get("current_location", "")).strip().lower()
    prov = str(state.get("current_province", "")).strip().lower()
    stage = state.get("quest_stage", 10)

    # If player is outside the Imperial Dungeon, Stage 10 is accomplished
    if stage <= 10 and loc and "imperial dungeon" not in loc:
        state["quest_stage"] = 20
        flags = state.setdefault("world_flags", {})
        flags["province_travel_unlocked"] = True
        save_world_state(character_name, state)

    return state



