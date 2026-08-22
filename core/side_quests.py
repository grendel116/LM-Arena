import os
import json
import time
import uuid
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def load_active_side_quests() -> list:
    """Loads active side quests from the active save bundle."""
    try:
        from core.save_manager import get_active_save_id, read_save
        save_id = get_active_save_id()
        if save_id:
            bundle = read_save(save_id)
            if bundle and isinstance(bundle.get("side_quests"), list):
                return bundle["side_quests"]
    except Exception as e:
        print(f"[load_active_side_quests] Error reading save bundle: {e}")
    return []

def save_active_side_quests(quests: list) -> None:
    """Saves active side quests directly to the active save bundle."""
    try:
        from core.save_manager import get_active_save_id, read_save, write_save
        save_id = get_active_save_id()
        if save_id:
            bundle = read_save(save_id)
            if bundle:
                bundle["side_quests"] = quests
                write_save(save_id, bundle)
    except Exception as e:
        print(f"[save_active_side_quests] Error writing save bundle: {e}")

def load_archived_side_quests() -> list:
    """Loads archived side quests from the active save bundle."""
    try:
        from core.save_manager import get_active_save_id, read_save
        save_id = get_active_save_id()
        if save_id:
            bundle = read_save(save_id)
            if bundle and isinstance(bundle.get("archived_side_quests"), list):
                return bundle["archived_side_quests"]
    except Exception as e:
        print(f"[load_archived_side_quests] Error reading save bundle: {e}")
    return []

def save_archived_side_quests(history: list) -> None:
    """Saves archived side quests directly to the active save bundle."""
    try:
        from core.save_manager import get_active_save_id, read_save, write_save
        save_id = get_active_save_id()
        if save_id:
            bundle = read_save(save_id)
            if bundle:
                bundle["archived_side_quests"] = history
                write_save(save_id, bundle)
    except Exception as e:
        print(f"[save_archived_side_quests] Error writing save bundle: {e}")

def parse_objectives_into_stages(raw_notes: str) -> list:
    """Parses raw text into discrete sequential stages (10, 20, 30...)."""
    clean_notes = str(raw_notes).replace('\\n', '\n')
    lines = [line.strip() for line in clean_notes.split('\n') if line.strip()]
    if not lines:
        lines = [str(raw_notes).strip()]

    stages = []
    total = len(lines)
    for i, line in enumerate(lines):
        stage_num = (i + 1) * 10
        is_last = (i == total - 1)
        next_num = None if is_last else (i + 2) * 10
        stages.append({
            "stage": stage_num,
            "objective": line,
            "next_stage": next_num,
            "is_complete": is_last
        })
    return stages

def create_side_quest(title: str, notes: str, due: str = None, location: str = "", reminder_minutes: int = 15) -> dict:
    """Creates a structured, staged side quest and saves it to the active quest log."""
    quests = load_active_side_quests()
    
    # Avoid exact duplicate titles in active log
    for q in quests:
        if q.get("title", "").strip().lower() == title.strip().lower():
            return {"status": "exists", "quest": q, "message": f"Side quest '{title}' already exists."}

    stages = parse_objectives_into_stages(notes)
    
    # Parse due time
    due_val = due
    if not due_val:
        due_val = datetime.now(timezone.utc).isoformat()
    else:
        due_lower = str(due_val).lower()
        if "tomorrow" in due_lower:
            due_val = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        elif "today" in due_lower:
            due_val = datetime.now(timezone.utc).isoformat()
        else:
            match_hours = re.search(r'in\s+(\d+)\s+hour', due_lower)
            match_days = re.search(r'in\s+(\d+)\s+day', due_lower)
            if match_hours:
                hours = int(match_hours.group(1))
                due_val = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
            elif match_days:
                days = int(match_days.group(1))
                due_val = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
            else:
                try:
                    datetime.fromisoformat(str(due_val).replace("Z", "+00:00"))
                except Exception:
                    due_val = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    try:
        rem_min = int(reminder_minutes)
    except (ValueError, TypeError):
        rem_min = 15

    ts = int(time.time())
    suffix = uuid.uuid4().hex[:6]
    quest_id = f"sq_{ts}_{suffix}"

    first_obj = stages[0]["objective"] if stages else title
    quest = {
        "id": quest_id,
        "title": title.strip(),
        "location": location.strip(),
        "stage": 10,
        "stages": stages,
        "active_objective": first_obj,
        "next_stage": stages[0].get("next_stage") if stages else None,
        "due": due_val,
        "reminder_minutes": rem_min,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_main_quest": False
    }

    quests.append(quest)
    save_active_side_quests(quests)
    return {"status": "success", "quest": quest, "message": f"Created side quest '{title}' with {len(stages)} stages."}

def advance_side_quest(quest_id: str = None, target_stage: int = None, **kwargs) -> dict:
    """Advances a side quest to its next sequential stage or marks it completed."""
    quests = load_active_side_quests()
    if not quests:
        return {"status": "error", "message": "No active side quests in the journal."}

    target_quest = None
    if quest_id:
        for q in quests:
            if q.get("id") == quest_id or q.get("title", "").lower() == str(quest_id).lower():
                target_quest = q
                break
    else:
        # Default to the most recently created active side quest
        target_quest = quests[-1]

    if not target_quest:
        return {"status": "error", "message": f"Side quest '{quest_id}' not found."}

    cur_stage_num = target_quest.get("stage", 10)
    stages = target_quest.get("stages", [])

    # Find the current stage object
    cur_stage_obj = None
    for s in stages:
        if s.get("stage") == cur_stage_num:
            cur_stage_obj = s
            break

    if target_stage is not None:
        new_stage_num = int(target_stage)
        target_quest["stage"] = new_stage_num
        new_stage_obj = next((s for s in stages if s.get("stage") == new_stage_num), None)
        if new_stage_obj:
            target_quest["active_objective"] = new_stage_obj.get("objective", "")
            target_quest["next_stage"] = new_stage_obj.get("next_stage")
        save_active_side_quests(quests)
        return {
            "status": "success",
            "quest_id": target_quest["id"],
            "quest_title": target_quest["title"],
            "previous_stage": cur_stage_num,
            "current_stage": new_stage_num,
            "active_objective": target_quest.get("active_objective", "")
        }

    # Deterministic next stage from current stage definition
    next_stage_num = cur_stage_obj.get("next_stage") if cur_stage_obj else None
    is_complete = cur_stage_obj.get("is_complete", False) if cur_stage_obj else False

    if next_stage_num is None or is_complete:
        # Quest is finished! Move to archive.
        quests = [q for q in quests if q.get("id") != target_quest["id"]]
        save_active_side_quests(quests)

        history = load_archived_side_quests()
        archived_entry = {
            "id": target_quest["id"],
            "title": target_quest["title"],
            "objectives": [s.get("objective") for s in stages if s.get("objective")],
            "location": target_quest.get("location", ""),
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        history.append(archived_entry)
        save_archived_side_quests(history)

        return {
            "status": "success",
            "completed": True,
            "quest_id": target_quest["id"],
            "quest_title": target_quest["title"],
            "message": f"Side quest '{target_quest['title']}' completed and archived!"
        }

    # Step to next stage
    target_quest["stage"] = next_stage_num
    new_stage_obj = next((s for s in stages if s.get("stage") == next_stage_num), None)
    if new_stage_obj:
        target_quest["active_objective"] = new_stage_obj.get("objective", "")
        target_quest["next_stage"] = new_stage_obj.get("next_stage")

    save_active_side_quests(quests)
    return {
        "status": "success",
        "quest_id": target_quest["id"],
        "quest_title": target_quest["title"],
        "previous_stage": cur_stage_num,
        "current_stage": next_stage_num,
        "active_objective": target_quest.get("active_objective", ""),
        "next_stage": target_quest.get("next_stage")
    }

def complete_side_quest(quest_id: str) -> dict:
    """Immediately completes and archives a side quest."""
    return advance_side_quest(quest_id=quest_id, target_stage=None)

def get_side_quest_display_data() -> tuple[list, list]:
    """Formats active and completed side quests with granular checkbox objects."""
    raw_active = load_active_side_quests()
    raw_archived = load_archived_side_quests()

    formatted_active = []
    for q in raw_active:
        cur_st = q.get("stage", 10)
        stages = q.get("stages", [])
        
        # If legacy side quest without stages, auto-upgrade
        if not stages:
            raw_objs = q.get("objectives", [q.get("title", "")])
            stages = parse_objectives_into_stages("\n".join(raw_objs) if isinstance(raw_objs, list) else str(raw_objs))
            q["stages"] = stages
            q["stage"] = cur_st

        objs = []
        for s in stages:
            s_num = s.get("stage", 0)
            objs.append({
                "text": s.get("objective", ""),
                "completed": s_num < cur_st,
                "active": s_num == cur_st
            })

        curr_stage_obj = next((s for s in stages if s.get("stage") == cur_st), stages[0] if stages else {})
        formatted_active.append({
            "id": q.get("id"),
            "title": q.get("title", "Side Quest"),
            "location": q.get("location", ""),
            "due": q.get("due", "Active Side Quest"),
            "stage_number": cur_st,
            "active_objective": curr_stage_obj.get("objective", ""),
            "next_stage": curr_stage_obj.get("next_stage"),
            "objectives": objs,
            "is_main_quest": False
        })

    formatted_archived = []
    for cq in raw_archived:
        formatted_archived.append({
            "id": cq.get("id"),
            "title": cq.get("title", "Side Quest"),
            "objectives": cq.get("objectives", []),
            "status": cq.get("status", "completed"),
            "is_main_quest": False
        })

    return formatted_active, formatted_archived
