"""
core/tool_agent.py — Subagent layer for state-mutating tools.

Each wrapped tool no longer executes blindly. A small LLM call (the "subagent") sees the real
game state (inventory, vitals, foes, quest...), the scene narration, the user's message, and the
tool calls already made recently, then returns a verdict: apply, adjust (corrected arguments),
or reject (with a reason the Game model can read and narrate around).

Dice, math and persistence stay in deterministic Python. The subagent only decides whether the
call matches what actually happened and which arguments are correct. If no model can be reached
the call is applied unchanged (fail-open), so a downed server never blocks gameplay.
"""
import contextvars
import functools
import inspect
import json
import os
import re
import threading

_turn_ctx: contextvars.ContextVar = contextvars.ContextVar("tool_agent_turn_ctx", default=None)
_ctx_lock = threading.Lock()

_THINK_RE = re.compile(r"(?:<think>|\[think\])[\s\S]*?(?:</think>|\[/think\]|$)", re.IGNORECASE)

_ROLE_RULES = {
    "inventory": (
        "You are the Inventory Clerk for a roleplaying game. Validate one proposed inventory or gold call "
        "against the character's real inventory and what the narration actually shows.\n"
        "Rules:\n"
        "- Using, examining, wielding, or unlocking with an item the player already holds is NOT acquiring it. "
        "Reject adding an item that is already held unless the narration clearly shows an additional, separate one being obtained.\n"
        "- If the proposed item is the same thing as a held item under a different name, adjust item_name to the held item's exact name.\n"
        "- Reject removing an item that is not held (name the nearest held item in the reason if any). "
        "Using an item does not remove it unless it is consumed, given away, sold, or destroyed.\n"
        "- Reject spending more gold than held. Reject awarding or spending gold that a recent tool call already applied for the same event.\n"
        "- Keep quantities realistic and positive."
    ),
    "combat": (
        "You are the Combat Adjudicator for a roleplaying game. Dice and damage math are done by code; you only validate and correct inputs.\n"
        "Rules:\n"
        "- Attackers and targets must actually be present in the scene per the narration. Reject invented combatants. "
        "The active foe list is only a tracker: the tools create a foe entry on first contact, so a creature missing from that list is NOT grounds for rejection when the narration shows it.\n"
        "- arena_roll_combat already applies damage to the player when a hit lands, so reject arena_take_damage for the same blow.\n"
        "- arena_damage_target is only for the player's own attack or spell that the narration says was resolved and succeeded. "
        "Use the exact foe name from the active foe list when the proposed name refers to the same creature.\n"
        "- Damage tiers must be plausible for the weapon or spell (1 weak to 5 devastating). Adjust absurd values.\n"
        "- arena_heal only when something in the narration actually restores health (potion, spell, rest). Reject repeats of a heal already applied."
    ),
    "state": (
        "You are the State Keeper for a roleplaying game. Validate one proposed world or character state change.\n"
        "Rules:\n"
        "- Location changes only when the narration shows the player actually moving there. Reject otherwise.\n"
        "- Quest stages advance only when the current objective is genuinely completed in the narration, and only to the stage that follows it.\n"
        "- Do not add an effect or condition that is already active. Remove effects only if the narration ends them.\n"
        "- XP only for a real accomplishment, never twice for the same event, and keep amounts proportionate.\n"
        "- Reject repeats of a call a recent tool call already applied for the same event."
    ),
}

_OUTPUT_SPEC = (
    "Reply with ONE JSON object and nothing else:\n"
    '{"decision": "apply" | "adjust" | "reject", "args": {<only the corrected arguments, for adjust>}, "reason": "<one short sentence>"}'
)


def is_enabled() -> bool:
    return os.getenv("TOOL_AGENTS_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")


def set_turn_context(save_id: str, narration: str = "", user_message: str = "", recent_messages: list | None = None) -> None:
    """Called by the runner before executing tool calls so subagents can see the scene."""
    recent_calls = []
    for msg in (recent_messages or [])[-8:]:
        calls = {}
        for tc in msg.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            if tc.get("type") == "call":
                calls[tc.get("id")] = {"name": tc.get("name"), "args": tc.get("args")}
            elif tc.get("type") == "response" and tc.get("id") in calls:
                calls[tc["id"]]["response"] = str(tc.get("response"))[:200]
        recent_calls.extend(calls.values())
    _turn_ctx.set({
        "save_id": save_id,
        "narration": (narration or "").strip()[-1800:],
        "user_message": (user_message or "").strip()[-600:],
        "recent_calls": recent_calls[-10:],
        "turn_calls": [],
    })


def _extract_json(text: str) -> dict | None:
    text = _THINK_RE.sub("", text or "").strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _chat(messages: list) -> str:
    import requests
    from variables.settings import LOCAL_SERVER_URL, get_local_server_headers, is_thinking_enabled, DISABLED_THINKING

    payload = {"messages": messages, "temperature": 0.1, "max_tokens": 300}
    if not is_thinking_enabled() and isinstance(DISABLED_THINKING, dict):
        payload.update(DISABLED_THINKING)
    model = os.getenv("TOOL_AGENT_MODEL") or os.getenv("LOCAL_MODEL_NAME")
    if model:
        payload["model"] = model

    try:
        resp = requests.post(LOCAL_SERVER_URL, json=payload, headers=get_local_server_headers(), timeout=60)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"].get("content", "") or ""
        print(f"[tool_agent] Server returned {resp.status_code}", flush=True)
    except Exception as e:
        print(f"[tool_agent] Server unreachable ({e}); trying in-process engine", flush=True)

    try:
        from runners import engine_llm
        if engine_llm.is_loaded():
            return engine_llm.generate_text(messages, 0.1, 300)
    except Exception:
        pass
    return ""


def _fmt_items(inventory: list) -> str:
    parts = []
    for i in inventory:
        qty = i.get("quantity", 1)
        tag = f" x{qty}" if qty > 1 else ""
        eq = " [equipped]" if i.get("equipped") else ""
        parts.append(f"{i.get('name')}{tag} ({i.get('type', 'Item')}){eq}")
    return "; ".join(parts) or "empty"


def _build_state(domain: str, tool_name: str, proposal: dict) -> str:
    lines = []
    try:
        from core.save_manager import get_active_save_id
        from core.character import load_character
        from core.world_engine import load_world_state
        save_id = get_active_save_id()
        sheet = load_character(save_id) or {}
        world = load_world_state(save_id) or {}
        d = sheet.get("derived", {})

        if domain == "inventory":
            inv = sheet.get("inventory", [])
            lines.append(f"Gold: {sheet.get('gold', 0)}")
            lines.append(f"Inventory: {_fmt_items(inv)}")
            name = str(proposal.get("item_name") or "").strip().lower()
            if name:
                held = next((i for i in inv if str(i.get("name", "")).lower() == name), None)
                if held:
                    lines.append(f"NOTE: '{held['name']}' is ALREADY HELD (quantity {held.get('quantity', 1)}).")
                else:
                    lines.append(f"NOTE: '{proposal.get('item_name')}' is not currently held under that exact name.")
        elif domain == "combat":
            lines.append(f"Player: {sheet.get('name', 'Hero')} HP {d.get('hp_current')}/{d.get('hp_max')} | "
                         f"MP {d.get('mp_current')}/{d.get('mp_max')} | Stamina {d.get('stamina_current')}/{d.get('stamina_max')}")
            equipped = [i.get("name") for i in sheet.get("inventory", []) if i.get("equipped")]
            lines.append(f"Equipped: {', '.join(equipped) or 'none'}")
            lines.append(f"Spells: {', '.join(str(s.get('name')) for s in sheet.get('spells', [])) or 'none'}")
            foes = world.get("foes", {}) or {}
            foe_txt = ", ".join(f"{k} (HP {v.get('hp_current')}/{v.get('hp_max')})" for k, v in foes.items())
            lines.append(f"Active foes: {foe_txt or 'none'}")
            lines.append(f"Location: {world.get('current_location')}")
        else:
            date = world.get("date") or world.get("tamrielic_date") or {}
            lines.append(f"Location: {world.get('current_location')} ({world.get('current_province')})")
            lines.append(f"Date: {date.get('day')} {date.get('month')}, hour {date.get('hour')}")
            lines.append(f"Quest stage: {world.get('quest_stage')}")
            try:
                from core.quest_tracker import load_quest_stages, get_current_stage
                stage = get_current_stage(world.get("quest_stage", 10), load_quest_stages())
                if stage:
                    lines.append(f"Current objective: {stage.get('objective', '')} | Next stage: {stage.get('next_stage', '')}")
            except Exception:
                pass
            lines.append(f"Active effects: {', '.join(e.get('name', '?') for e in sheet.get('active_effects', [])) or 'none'}")
            lines.append(f"Conditions: {', '.join(map(str, sheet.get('conditions', []))) or 'none'}")
            lines.append(f"Level {sheet.get('level', 1)}, XP {sheet.get('experience', 0)}")
    except Exception as e:
        lines.append(f"(state unavailable: {e})")
    return "\n".join(lines)


def _consult(domain: str, tool_name: str, proposal: dict) -> dict | None:
    ctx = _turn_ctx.get() or {}
    prior = (ctx.get("recent_calls") or []) + (ctx.get("turn_calls") or [])
    prior_txt = "\n".join(
        f"- {c.get('name')}({c.get('args')}) -> {c.get('response', 'applied')}" for c in prior[-12:]
    ) or "none"

    user = (
        f"## Current state\n{_build_state(domain, tool_name, proposal)}\n\n"
        f"## Player's latest message\n{ctx.get('user_message') or '(none)'}\n\n"
        f"## Scene narration this turn\n{ctx.get('narration') or '(none)'}\n\n"
        f"## Tool calls already made recently\n{prior_txt}\n\n"
        f"## Proposed call\n{tool_name}({json.dumps(proposal, default=str)})\n\n"
        f"{_OUTPUT_SPEC}"
    )
    raw = _chat([
        {"role": "system", "content": _ROLE_RULES[domain]},
        {"role": "user", "content": user},
    ])
    verdict = _extract_json(raw)
    if not verdict or str(verdict.get("decision", "")).lower() not in ("apply", "adjust", "reject"):
        return None
    verdict["decision"] = str(verdict["decision"]).lower()
    return verdict


def tool_agent(domain: str):
    """Decorator: route a tool call through a subagent verdict before executing it."""
    if domain not in _ROLE_RULES:
        raise ValueError(f"Unknown tool agent domain: {domain}")

    def decorator(func):
        sig = inspect.signature(func)
        var_kinds = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        named = [n for n, p in sig.parameters.items() if p.kind not in var_kinds]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not is_enabled():
                return func(*args, **kwargs)

            try:
                bound = sig.bind_partial(*args, **kwargs)
                proposal = {k: v for k, v in bound.arguments.items() if k in named and v is not None}
                proposal.update({k: v for k, v in kwargs.items() if k not in named})
            except TypeError:
                proposal = dict(kwargs)

            try:
                verdict = _consult(domain, func.__name__, proposal)
            except Exception as e:
                print(f"[tool_agent] {func.__name__} consult failed: {e}", flush=True)
                verdict = None

            ctx = _turn_ctx.get()
            decision = (verdict or {}).get("decision", "apply")
            reason = str((verdict or {}).get("reason") or "").strip()

            if decision == "reject":
                if ctx is not None:
                    ctx["turn_calls"].append({"name": func.__name__, "args": proposal, "response": f"rejected: {reason}"})
                return {
                    "success": False,
                    "verdict": "rejected",
                    "reason": reason or "The call does not match the current game state.",
                    "state": _build_state(domain, func.__name__, proposal),
                }

            result = None
            if decision == "adjust" and isinstance(verdict.get("args"), dict) and verdict["args"]:
                allowed = set(named) | set(proposal)
                fixes = {k: v for k, v in verdict["args"].items() if k in allowed}
                if fixes:
                    merged = {**{k: v for k, v in proposal.items()}, **fixes}
                    result = func(**merged)
                    if isinstance(result, dict):
                        result = {**result, "verdict": "adjusted", "note": reason, "applied_args": fixes}
                    proposal = merged

            if result is None:
                result = func(*args, **kwargs)

            if ctx is not None:
                ctx["turn_calls"].append({"name": func.__name__, "args": proposal, "response": "applied"})
            return result

        return wrapper

    return decorator
