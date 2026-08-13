import os

arena_code = """
# --- Arena Additions ---
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.mechanics import roll_check, roll_combat, roll_initiative, roll_skill, sorcerer_absorb
from engine.world_engine import load_world_state, save_world_state, get_location_context, travel, advance_time, set_flag, discover_location
from engine.quest_tracker import load_quest_stages, get_stage_context_injection, check_stage_conditions, advance_stage
from engine.spellmaker import evaluate_spell, get_school_for_effect

@track_tool_activity
def arena_roll_check(attribute_name, attribute_value, dc, advantage=False, disadvantage=False):
    \"\"\"Roll a d20 attribute check for the current scene. Results appear as a collapsible tool call. The LLM narrates only the outcome, never the numbers.\"\"\"
    return roll_check(attribute_name, attribute_value, dc, advantage, disadvantage)

@track_tool_activity
def arena_roll_combat(attacker_name, attacker_strength, attacker_agility, attacker_class_archetype, weapon_name, weapon_damage_tier, weapon_attribute, target_name, target_agility):
    \"\"\"Resolve a combat attack roll. Results are shown in the collapsible tool call log.\"\"\"
    attacker = {
        "name": attacker_name,
        "strength": attacker_strength,
        "agility": attacker_agility,
        "class_archetype": attacker_class_archetype
    }
    target = {
        "name": target_name,
        "agility": target_agility
    }
    weapon = {
        "name": weapon_name,
        "damage_tier": weapon_damage_tier,
        "attribute": weapon_attribute
    }
    return roll_combat(attacker, target, weapon)

@track_tool_activity
def arena_roll_initiative(combatants_json):
    \"\"\"Roll initiative for all combatants in a combat encounter.\"\"\"
    import json
    combatants = json.loads(combatants_json)
    return roll_initiative(combatants)

@track_tool_activity
def arena_roll_skill(skill_name, attribute_name, attribute_value, dc):
    \"\"\"Roll a skill check (lockpicking, stealth, persuasion, etc.) using the d20 narrative system.\"\"\"
    return roll_skill(skill_name, attribute_name, attribute_value, dc)

@track_tool_activity
def arena_sorcerer_absorb(intelligence, willpower, incoming_spell_tier):
    \"\"\"Check if a Sorcerer's passive Spell Absorption activates against an incoming spell.\"\"\"
    return sorcerer_absorb(intelligence, willpower, incoming_spell_tier)

@track_tool_activity
def arena_get_location(character_name):
    \"\"\"Get the current location context for the active character.\"\"\"
    import json
    world_state = load_world_state(character_name)
    with open(os.path.join(os.path.dirname(__file__), "core", "world", "provinces.json"), "r") as f:
        provinces = json.load(f)
    with open(os.path.join(os.path.dirname(__file__), "core", "world", "cities.json"), "r") as f:
        cities = json.load(f)
    with open(os.path.join(os.path.dirname(__file__), "core", "world", "dungeons.json"), "r") as f:
        dungeons = json.load(f)
    return get_location_context(world_state, provinces, cities, dungeons)

@track_tool_activity
def arena_travel(character_name, destination_province, destination_city):
    \"\"\"Travel to a new province and city. Updates world state and advances time.\"\"\"
    world_state = load_world_state(character_name)
    travel_summary = travel(world_state, destination_province, destination_city)
    save_world_state(character_name, world_state)
    return travel_summary

@track_tool_activity
def arena_advance_stage(character_name):
    \"\"\"Check if the current quest stage conditions are met and advance if so.\"\"\"
    world_state = load_world_state(character_name)
    stages = load_quest_stages()
    fired = advance_stage(world_state, stages)
    save_world_state(character_name, world_state)
    return fired

@track_tool_activity
def arena_create_spell(spell_description, school, tier, caster_intelligence):
    \"\"\"Create a new spell using the Spellmaker. Returns a spell card to add to the character sheet.\"\"\"
    evaluation = evaluate_spell(spell_description, tier)
    assigned_school = get_school_for_effect(evaluation['effect_type'])
    evaluation['school'] = assigned_school
    return evaluation
"""

with open("c:\\LLM\\LM-Arena\\tools.py", "a", encoding="utf-8") as f:
    f.write("\\n" + arena_code)
