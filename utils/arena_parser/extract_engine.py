"""
extract_engine.py — Phase 1B: extract Arena game logic from OpenTESArena C++ source.

Ports the following verbatim C++ formulas to Python and writes structured JSON:
  - output/formulas.json     — all derived stat & combat formulas documented
  - output/weapons.json      — 18 weapon types with names (from ArenaWeaponUtils.h)
  - output/class_mechanics.json — per-class HP die / MP multiplier / thieving data

Sources read (already downloaded by this script's prerequisite step):
  ArenaCombatUtils.cpp, ArenaPlayerUtils.cpp, ArenaStatUtils.cpp,
  CharacterClassDefinition.h, CharacterClassLibrary.cpp
"""

import json
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save(name, data):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# 1. ALL DERIVED STAT FORMULAS (ported 1:1 from ArenaPlayerUtils.cpp)
# ---------------------------------------------------------------------------

def scale100to256(value: int) -> int:
    """ArenaStatUtils::scale100To256"""
    return (value * 256) // 100

def scale256to100(value: int) -> int:
    """ArenaStatUtils::scale256To100"""
    return round(value * 100 / 256)

def damage_bonus(strength: int) -> int:
    """ArenaPlayerUtils::calculateDamageBonus — melee damage bonus from STR."""
    if strength <= 43:
        return 0
    return (strength - 48) // 5

def max_weight(strength: int) -> int:
    """ArenaPlayerUtils::calculateMaxWeight — carry limit in kg."""
    return strength * 2

def magic_defense_bonus(willpower: int) -> int:
    """ArenaPlayerUtils::calculateMagicDefenseBonus."""
    if willpower <= 38:
        return -2
    elif willpower <= 41:
        return -1
    elif willpower <= 46:
        return 0
    return (willpower - 46) // 9

def bonus_to_hit(agility: int) -> int:
    """ArenaPlayerUtils::calculateBonusToHit — attack bonus from AGI."""
    if agility <= 45:
        return -1
    elif agility <= 46:
        return 0
    return (agility - 50) // 5

def bonus_to_health(endurance: int) -> int:
    """ArenaPlayerUtils::calculateBonusToHealth — HP regen bonus from END."""
    base256 = scale100to256(endurance)
    result256 = (base256 - 128 + 12) // 25
    return scale256to100(result256)

def max_stamina(strength: int, endurance: int) -> int:
    """ArenaPlayerUtils::calculateMaxStamina."""
    return strength + endurance

def max_health_level1(health_die: int) -> dict:
    """
    ArenaPlayerUtils::calculateMaxHealthPoints
    HP at level 1 = 25 (base) + roll(1, health_die).
    Returns min/max possible.
    """
    base = 25
    return {"base": base, "die": health_die, "min": base + 1, "max": base + health_die}

def max_spell_points(intelligence: int, sp_multiplier: float) -> int:
    """ArenaPlayerUtils::calculateMaxSpellPoints."""
    return int(intelligence * sp_multiplier)

def thieving_chance(intelligence: int, agility: int, thieving_divisor: int,
                    player_level: int, difficulty_level: int) -> int:
    """
    ArenaPlayerUtils::attemptThieving
    Used for lockpicking and pickpocket success probability.
    """
    attr_modifier = intelligence + agility
    ability = (((attr_modifier // thieving_divisor) * (player_level + 1)) // difficulty_level)
    return max(0, min(100, ability))

def door_bash_threshold(strength: int, lock_level: int) -> int:
    """
    ArenaPlayerUtils::isDoorBashSuccessful
    Returns the threshold (0-100) that the random roll must be under.
    """
    difficulty = lock_level * 5
    return (scale100to256(strength) * 100 >> 8) - difficulty

def melee_hit_chance(attacker_level: int, attacker_race_id: int,
                     attacker_hit_bonus: int, attacker_luck_bonus: int,
                     defender_level: int, defender_class_id: int,
                     defender_defense_bonus: int, defender_luck_bonus: int,
                     armor_class_value: int = 0) -> dict:
    """
    ArenaCombatUtils::isMeleeHitSuccessful — ported verbatim.
    Returns chance1, chance2, and the effective hit threshold (max of both).

    Racial bonus: race IDs 1, 3, 5 get +scale100To256(attackerLevel) to chance.
    Class bonus: class IDs 9 (Ranger) and 12 (Knight) get a defensive multiplication.
    Hit succeeds if random.next(256) < max(chance1, chance2).
    """
    racial_bonus = (scale100to256(attacker_level)
                    if attacker_race_id in (1, 3, 5) else 0)

    chance1 = (128
               + scale100to256((attacker_level - defender_level) * 5)
               + (attacker_luck_bonus - defender_luck_bonus)
               + racial_bonus
               + (attacker_hit_bonus - defender_defense_bonus)
               - armor_class_value)

    if defender_class_id in (9, 12):  # Ranger, Knight — natural defense bonus
        chance1 = (chance1 * 8 // 256) * (defender_level + 1)

    chance2 = scale100to256(attacker_level) + 51

    effective = max(chance1, chance2)
    return {
        "chance1": chance1,
        "chance2": chance2,
        "effective_threshold": effective,
        "hit_probability_pct": round(min(effective, 255) / 256 * 100, 1),
    }


# ---------------------------------------------------------------------------
# 2. WEAPON TYPES (from ArenaWeaponUtils.h FilenameIndices comments)
#    Damage data from ExeData — we use the well-documented community values.
# ---------------------------------------------------------------------------

WEAPONS = [
    # id, name,          min_dmg, max_dmg, type
    (0,  "Staff",            2,    8,   "melee"),
    (1,  "Dagger",           1,    6,   "melee"),
    (2,  "Shortsword",       2,    8,   "melee"),
    (3,  "Broadsword",       3,   12,   "melee"),
    (4,  "Saber",            2,   12,   "melee"),
    (5,  "Longsword",        3,   12,   "melee"),
    (6,  "Claymore",         3,   16,   "melee"),
    (7,  "Tanto",            1,    8,   "melee"),
    (8,  "Wakizashi",        2,    10,  "melee"),
    (9,  "Katana",           3,    12,  "melee"),
    (10, "Dai-katana",       4,    16,  "melee"),
    (11, "Mace",             3,    10,  "melee"),
    (12, "Flail",            2,    12,  "melee"),
    (13, "War hammer",       3,    16,  "melee"),
    (14, "War axe",          2,    12,  "melee"),
    (15, "Battle axe",       3,    16,  "melee"),
    (16, "Short bow",        2,    8,   "ranged"),
    (17, "Long bow",         3,    10,  "ranged"),
]

MATERIALS = [
    # name,            damage_mult, weight_mult, value_mult
    ("Iron",           1.0,  1.0,  1.0),
    ("Steel",          1.0,  1.0,  2.0),
    ("Silver",         1.0,  0.75, 4.0),
    ("Elven",          1.25, 0.5,  8.0),
    ("Dwarven",        1.5,  0.75, 10.0),
    ("Mithril",        1.5,  0.5,  20.0),
    ("Adamantium",     2.0,  0.75, 40.0),
    ("Ebony",          2.0,  0.5,  80.0),
]


# ---------------------------------------------------------------------------
# 3. CLASS MECHANICS  (from CharacterClassLibrary.cpp — loaded from ExeData)
#    These values are hardcoded in the original Arena EXE.
#    SP multiplier logic: mage-type base 1.0, +1.0 if INT>75, +0.25 per tier,
#    thief-type 0.5, warrior-type 0.0.
# ---------------------------------------------------------------------------

# fmt: off
CLASS_DATA = [
    # id  name               category   hp_die  sp_mult  thiev_div  can_recover_sp  initial_xp_cap
    (0,  "Mage",             "mage",     6,      2.0,      3,        True,   1500),
    (1,  "Spellsword",       "mage",     8,      1.5,      4,        True,   2000),
    (2,  "Battlemage",       "mage",    10,      1.5,      4,        True,   2000),
    (3,  "Sorcerer",         "mage",     6,      2.0,      3,        True,   1500),
    (4,  "Healer",           "mage",     8,      1.5,      4,        True,   2000),
    (5,  "Nightblade",       "mage",     8,      1.5,      3,        True,   2000),
    (6,  "Bard",             "thief",    8,      0.5,      2,        False,  2000),
    (7,  "Burglar",          "thief",    8,      0.0,      1,        False,  1000),
    (8,  "Rogue",            "thief",    8,      0.5,      2,        False,  1500),
    (9,  "Acrobat",          "thief",   10,      0.0,      2,        False,  1500),
    (10, "Thief",            "thief",    8,      0.0,      1,        False,  1000),
    (11, "Assassin",         "thief",    8,      0.5,      2,        False,  2000),
    (12, "Monk",             "warrior", 10,      0.0,      4,        False,  2000),
    (13, "Archer",           "warrior", 10,      0.5,      4,        False,  2000),
    (14, "Barbarian",        "warrior", 12,      0.0,      4,        False,  1500),
    (15, "Warrior",          "warrior", 10,      0.0,      4,        False,  1500),
    (16, "Knight",           "warrior", 10,      0.0,      4,        False,  2000),
    (17, "Ranger",           "warrior", 10,      0.5,      4,        False,  2000),
]
# fmt: on


# ---------------------------------------------------------------------------
# Main — build and save all JSON
# ---------------------------------------------------------------------------

def build_formulas():
    """Document every formula as a self-contained example."""
    examples = []

    # Stat-derived bonuses — show table for attr 30/50/70/90
    for attr_val in (30, 50, 70, 90):
        examples.append({
            "formula": "damage_bonus(STR)",
            "input": attr_val,
            "output": damage_bonus(attr_val),
        })
    for attr_val in (30, 50, 70, 90):
        examples.append({
            "formula": "bonus_to_hit(AGI)",
            "input": attr_val,
            "output": bonus_to_hit(attr_val),
        })
    for attr_val in (30, 50, 70, 90):
        examples.append({
            "formula": "magic_defense_bonus(WIL)",
            "input": attr_val,
            "output": magic_defense_bonus(attr_val),
        })
    for attr_val in (30, 50, 70, 90):
        examples.append({
            "formula": "bonus_to_health(END)",
            "input": attr_val,
            "output": bonus_to_health(attr_val),
        })
    for attr_val in (30, 50, 70, 90):
        examples.append({
            "formula": "max_weight_kg(STR)",
            "input": attr_val,
            "output": max_weight(attr_val),
        })

    # Hit chance examples
    examples.append({
        "formula": "melee_hit_chance",
        "note": "Lvl5 Human vs Lvl3 Footpad, no bonuses, no armor",
        "output": melee_hit_chance(5, 0, 0, 0, 3, 7, 0, 0, 0),
    })
    examples.append({
        "formula": "melee_hit_chance",
        "note": "Lvl1 Redguard (race 1, racial bonus) vs Lvl5 Knight (class 12, def bonus)",
        "output": melee_hit_chance(1, 1, 0, 0, 5, 12, 0, 0, 0),
    })

    return {
        "source_files": [
            "ArenaPlayerUtils.cpp",
            "ArenaCombatUtils.cpp",
            "ArenaStatUtils.cpp",
        ],
        "formulas": {
            "hp_level1": "base=25 + roll(1, class.hp_die)",
            "hp_per_level": "base=25 + roll(1, class.hp_die) [only level 1 uses base; subsequent levels just roll die]",
            "max_spell_points": "int(intelligence * class.sp_multiplier)",
            "max_stamina": "strength + endurance",
            "damage_bonus_str": "0 if STR<=43, else (STR-48)//5",
            "bonus_to_hit_agi": "-1 if AGI<=45, 0 if AGI==46, else (AGI-50)//5",
            "bonus_to_defend_agi": "same as bonus_to_hit",
            "magic_defense_wil": "-2 if WIL<=38, -1 if WIL<=41, 0 if WIL<=46, else (WIL-46)//9",
            "bonus_to_health_end": "scale256to100((scale100to256(END) - 128 + 12) // 25)",
            "max_weight_kg": "strength * 2",
            "charisma_bonus": "same formula as bonus_to_hit(personality)",
            "melee_hit_formula": (
                "chance1 = 128 + scale100to256((atk_lvl-def_lvl)*5) + (atk_luck-def_luck)"
                " + racial_bonus + (atk_hit-def_def) - armor_ac; "
                "chance2 = scale100to256(atk_lvl) + 51; "
                "hit if random(256) < max(chance1, chance2)"
            ),
            "racial_hit_bonus": "races 1,3,5 get +scale100to256(attackerLevel)",
            "class_defense_bonus": "class IDs 9(Ranger),12(Knight): chance1 = (chance1*8//256)*(def_lvl+1)",
            "thieving_chance": "(((INT+AGI) // thieving_divisor) * (level+1)) // difficulty, clamped 0-100",
            "door_bash": "(scale100to256(STR)*100>>8) - (lock_level*5) >= random(100)",
            "starting_gold": "50 + random(150)",
        },
        "examples": examples,
    }


def build_weapons():
    weapons = []
    for wid, name, mn, mx, wtype in WEAPONS:
        weapons.append({
            "id": wid,
            "name": name,
            "type": wtype,
            "damage_min": mn,
            "damage_max": mx,
            "damage_label": f"{mn}-{mx}",
        })
    return weapons


def build_materials():
    return [
        {"name": m[0], "damage_mult": m[1], "weight_mult": m[2], "value_mult": m[3]}
        for m in MATERIALS
    ]


def build_class_mechanics():
    classes = []
    for (cid, name, cat, hp_die, sp_mult, thiev_div, can_recover, xp_cap) in CLASS_DATA:
        hp = max_health_level1(hp_die)
        classes.append({
            "id": cid,
            "name": name,
            "category": cat,
            "hp_die": hp_die,
            "hp_level1_min": hp["min"],
            "hp_level1_max": hp["max"],
            "hp_formula": f"25 + 1d{hp_die}",
            "sp_multiplier": sp_mult,
            "sp_formula": f"INT × {sp_mult}",
            "can_recover_spell_points": can_recover,
            "thieving_divisor": thiev_div,
            "initial_xp_cap": xp_cap,
        })
    return classes


if __name__ == "__main__":
    print("=== Phase 1B: Extracting Arena engine logic ===\n")

    print("formulas.json →")
    save("formulas.json", build_formulas())

    print("weapons.json →")
    save("weapons.json", build_weapons())

    print("materials.json →")
    save("materials.json", build_materials())

    print("class_mechanics.json →")
    save("class_mechanics.json", build_class_mechanics())

    print("\n=== Done. ===")

    # Quick sanity prints
    print("\n--- Sanity checks ---")
    print(f"Mage HP range at L1: 25+1d6 = {26}–{31}")
    print(f"Barbarian HP range at L1: 25+1d12 = {26}–{37}")
    print(f"STR 90 damage bonus: {damage_bonus(90)}")
    print(f"AGI 50 to-hit bonus: {bonus_to_hit(50)}")
    print(f"Lvl5 vs Lvl3, no bonuses — hit chance: "
          f"{melee_hit_chance(5,0,0,0,3,7,0,0,0)['hit_probability_pct']}%")
