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
    """Returns the context_injection string or active objective for the current quest stage."""
    stage_num = state.get("quest_stage", 10)
    stage = get_current_stage(stage_num, stages)
    return stage.get("context_injection") or stage.get("objective", "")

def check_stage_conditions(state: dict, stage: dict) -> bool:
    """Checks all conditions in stage['conditions'] against state['world_flags']."""
    flags = state.get("world_flags", {})
    conditions = stage.get("conditions", {})
    for k, v in conditions.items():
        if flags.get(k) != v:
            return False
    return True


def advance_stage(state: dict, stages: list, force: bool = True) -> tuple[dict, list]:
    """Advances the quest stage to the immediate next stage and executes on_complete actions."""
    stage_num = state.get("quest_stage", 10)
    stage = get_current_stage(stage_num, stages)
    
    fired_actions = []
    
    next_stage_num = stage.get("next_stage")
    if next_stage_num is None:
        sorted_stages = sorted(stages, key=lambda x: x.get("stage", 0))
        for s in sorted_stages:
            if s.get("stage", 0) > stage_num:
                next_stage_num = s.get("stage", 0)
                break
        if next_stage_num is None:
            next_stage_num = stage_num
            
    if stage:
        for action in stage.get("on_complete", []):
            state = execute_action(state, action)
            fired_actions.append(action)
                    
    state["quest_stage"] = next_stage_num
    return state, fired_actions


def get_quest_display_data(current_stage_num: int, stages: list) -> tuple[list, list]:
    """Groups stages into active quest with granular checkboxes and archived completed quests."""
    if not stages:
        return [], []
        
    curr_stage = get_current_stage(current_stage_num, stages)
    curr_quest_id = curr_stage.get("quest_id")
    
    from collections import OrderedDict
    quest_groups = OrderedDict()
    for s in sorted(stages, key=lambda x: x.get("stage", 0)):
        qid = s.get("quest_id", "main_quest")
        if qid not in quest_groups:
            quest_groups[qid] = {
                "quest_id": qid,
                "quest_title": s.get("quest_title", "Main Quest"),
                "stages": []
            }
        quest_groups[qid]["stages"].append(s)
        
    active_quests = []
    completed_quests = []
    
    for qid, qdata in quest_groups.items():
        q_stages = qdata["stages"]
        is_quest_finished = all(s.get("stage", 0) < current_stage_num for s in q_stages) and (curr_quest_id != qid)
        
        if is_quest_finished:
            completed_quests.append({
                "id": f"completed_{qid}",
                "title": qdata["quest_title"],
                "objectives": [s.get("objective", "") for s in q_stages if s.get("objective")]
            })
        elif qid == curr_quest_id or any(s.get("stage", 0) == current_stage_num for s in q_stages):
            objs = []
            for s in q_stages:
                s_num = s.get("stage", 0)
                objs.append({
                    "text": s.get("objective", ""),
                    "completed": s_num < current_stage_num,
                    "active": s_num == current_stage_num
                })
            active_quests.append({
                "id": f"main_{qid}",
                "title": qdata["quest_title"],
                "stage_number": current_stage_num,
                "active_objective": curr_stage.get("objective", ""),
                "next_stage": curr_stage.get("next_stage"),
                "objectives": objs,
                "is_main_quest": True
            })
            
    return active_quests, completed_quests

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

def advance_quest_stage(arg1=None, target_stage: int = None, **kwargs) -> dict:
    """Advances the active save quest stage and saves the world state."""
    from core.world_engine import load_world_state, save_world_state
    if isinstance(arg1, (int, float)):
        stage_num_target = int(arg1)
    elif target_stage is not None:
        stage_num_target = int(target_stage)
    else:
        stage_num_target = None

    world_state = load_world_state()
    current_stage_num = world_state.get("quest_stage", 10)
    stages = load_quest_stages()

    if stage_num_target is not None:
        new_stage_num = stage_num_target
        stage = get_current_stage(current_stage_num, stages)
        fired_actions = []
        if stage:
            for action in stage.get("on_complete", []):
                world_state = execute_action(world_state, action)
                fired_actions.append(action)
        world_state["quest_stage"] = new_stage_num
    else:
        world_state, fired_actions = advance_stage(world_state, stages)
        new_stage_num = world_state.get("quest_stage", current_stage_num)

    save_world_state(world_state)
    new_stage = get_current_stage(new_stage_num, stages)
    
    q_title = new_stage.get("quest_title", f"Stage {new_stage_num}")
    q_obj = new_stage.get("objective", "")
    
    return {
        "status": "success",
        "previous_stage": current_stage_num,
        "current_stage": new_stage_num,
        "quest_title": q_title,
        "stage_label": f"{q_title} - Stage {new_stage_num}",
        "active_objective": q_obj,
        "objectives": [q_obj] if q_obj else [],
        "fired_actions": fired_actions
    }

def set_quest_stage(stage_number: int, **kwargs) -> dict:
    """Sets the character's quest stage directly."""
    return advance_quest_stage(target_stage=int(stage_number))

def sync_quest_stage_with_location(character_name: str = None) -> dict:
    """Auto-advances quest stage if the player has moved past earlier milestones in the narrative."""
    from core.world_engine import load_world_state, save_world_state
    state = load_world_state()
    loc = str(state.get("current_location", "")).strip().lower()
    stage = state.get("quest_stage", 10)

    # If player is outside the Imperial Dungeon, Stage 10 is accomplished
    if stage <= 10 and loc and "imperial dungeon" not in loc:
        state["quest_stage"] = 20
        flags = state.setdefault("world_flags", {})
        flags["province_travel_unlocked"] = True
        save_world_state(state)

    return state



