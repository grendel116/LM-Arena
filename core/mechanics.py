import os
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENTITIES_PATH = BASE_DIR / "core" / "world" / "entities.json"

# Global Damage Multipliers (Default 1.0 for authentic balance; configurable via .env)
INCOMING_DAMAGE_MULTIPLIER = float(os.getenv("INCOMING_DAMAGE_MULTIPLIER", "1.0"))
OUTGOING_DAMAGE_MULTIPLIER = float(os.getenv("OUTGOING_DAMAGE_MULTIPLIER", "1.0"))

_ENTITIES_CACHE = None

def load_entities() -> dict:
    """Loads pure mechanical entity definitions from core/world/entities.json."""
    global _ENTITIES_CACHE
    if _ENTITIES_CACHE is not None:
        return _ENTITIES_CACHE
    if os.path.exists(ENTITIES_PATH):
        try:
            with open(ENTITIES_PATH, "r", encoding="utf-8") as f:
                _ENTITIES_CACHE = json.load(f)
                return _ENTITIES_CACHE
        except Exception as e:
            print(f"[Entities] Error loading entities: {e}")
    return {}

# Alias for backward compatibility
load_bestiary = load_entities

def get_monster(name_or_key: str) -> dict:
    """Find a monster/entity mechanical template by key, alias, or substring match."""
    entities = load_entities()
    if not name_or_key:
        return {}
    
    clean_target = name_or_key.lower().strip()
    
    # Direct dictionary key lookup
    if clean_target in entities:
        ent = dict(entities[clean_target])
        ent["base_agility"] = ent.get("agility", 50)
        return ent
    
    # Alias / name / substring lookup
    for k, v in entities.items():
        aliases = [a.lower() for a in v.get("aliases", [])]
        name = v.get("name", "").lower()
        if clean_target == k or clean_target == name or clean_target in aliases or any(a in clean_target for a in aliases):
            ent = dict(v)
            ent["base_agility"] = ent.get("agility", 50)
            return ent
            
    return {}

# Authentic Arena Weapon Base Damage Ranges (from ExeData / ArenaWeaponUtils)
ARENA_WEAPONS = {
    "fists": (1, 2),
    "staff": (2, 8),
    "dagger": (1, 6),
    "shortsword": (2, 8),
    "broadsword": (3, 12),
    "saber": (2, 12),
    "longsword": (3, 12),
    "claymore": (3, 16),
    "tanto": (1, 8),
    "wakizashi": (2, 10),
    "katana": (3, 12),
    "dai-katana": (4, 16),
    "mace": (3, 10),
    "flail": (2, 12),
    "war hammer": (3, 16),
    "warhammer": (3, 16),
    "war axe": (2, 12),
    "battle axe": (3, 16),
    "battleaxe": (3, 16),
    "short bow": (2, 8),
    "shortbow": (2, 8),
    "long bow": (3, 10),
    "longbow": (3, 10)
}

# Authentic Arena Material Multipliers (from ItemMaterialLibrary)
MATERIAL_MULTIPLIERS = {
    "iron": 1.0,
    "steel": 1.0,
    "silver": 1.0,
    "elven": 1.25,
    "dwarven": 1.5,
    "mithril": 1.5,
    "adamantium": 2.0,
    "ebony": 2.0,
    "daedric": 2.0,
    "glass": 1.5
}

def calculate_damage_bonus(strength: int) -> int:
    """Arena formula: calculateDamageBonus."""
    if strength <= 43:
        return 0
    return (strength - 48) // 5

def calculate_to_hit_bonus(agility: int) -> int:
    """Arena formula: calculateBonusToHit."""
    if agility <= 45:
        return -1
    elif agility <= 46:
        return 0
    return (agility - 50) // 5

def calculate_magic_defense_bonus(willpower: int) -> int:
    """Arena formula: calculateMagicDefenseBonus."""
    if willpower <= 38:
        return -2
    elif willpower <= 41:
        return -1
    elif willpower <= 46:
        return 0
    return (willpower - 46) // 9

def get_modifier(attribute_value: int) -> int:
    """
    Returns general attribute modifier.
    Arena attributes are 0-100, centered at 50.
    """
    return round((attribute_value - 50) / 10)

def roll_check(attribute_name: str, attribute_value: int, dc: int, advantage: bool = False, disadvantage: bool = False) -> dict:
    """
    Rolls a d20 plus modifier against a DC.
    """
    if attribute_name.lower() == "agility":
        modifier = calculate_to_hit_bonus(attribute_value)
    else:
        modifier = get_modifier(attribute_value)
    
    roll1 = random.randint(1, 20)
    roll2 = random.randint(1, 20)
    
    if advantage and not disadvantage:
        base_roll = max(roll1, roll2)
    elif disadvantage and not advantage:
        base_roll = min(roll1, roll2)
    else:
        base_roll = roll1

    total = base_roll + modifier
    margin = total - dc
    success = total >= dc
    
    if base_roll == 20:
        degree = "critical"
        success = True
    elif base_roll == 1:
        degree = "fumble"
        success = False
    elif margin >= 0:
        degree = "success" if margin > 2 else "partial"
    else:
        degree = "failure"
        
    return {
        "roll": base_roll,
        "modifier": modifier,
        "total": total,
        "dc": dc,
        "success": success,
        "margin": margin,
        "degree": degree
    }

def roll_combat(attacker: dict, weapon: dict, target: dict) -> dict:
    """
    Attack resolution combining d20 degree-of-success narrative flow with authentic Arena weapon damage,
    material scaling, STR bonuses, and status tracking.
    """
    attr_name = weapon.get("attribute_used", "strength").lower()
    attr_value = attacker.get(attr_name, 50)
    
    # Look up bestiary template if target matches a known creature
    target_name = target.get("name", "Adversary")
    monster_data = get_monster(target_name) if not target.get("is_player") else {}
    
    target_agility = target.get("agility") or monster_data.get("base_agility", 50)
    defense_dc = 10 + calculate_to_hit_bonus(target_agility)
    
    # Low stamina / fatigue penalty
    attacker_stamina = attacker.get("stamina_current")
    attacker_stamina_max = attacker.get("stamina_max", 50)
    stamina_penalty = 0
    stamina_note = None
    is_exhausted = False
    if attacker_stamina is not None and attacker_stamina_max > 0:
        if attacker_stamina <= attacker_stamina_max * 0.25:
            is_exhausted = True
            stamina_penalty = -3
            stamina_note = "exhausted / low stamina (-3 to hit)"

    attack_res = roll_check(attr_name, attr_value, defense_dc, disadvantage=is_exhausted)
    if stamina_penalty:
        attack_res["total"] += stamina_penalty
        attack_res["margin"] += stamina_penalty
        attack_res["success"] = attack_res["total"] >= defense_dc
        if not attack_res["success"]:
            attack_res["degree"] = "failure"

    hit = attack_res["success"]
    margin = attack_res["margin"]
    degree = attack_res["degree"]
    
    damage_narrative = "miss"
    damage_dealt = 0
    status_effect = None
    
    weapon_name = weapon.get("name", "Fists").lower()
    weapon_material = weapon.get("material", "iron").lower()
    weapon_tier = weapon.get("damage_tier", 1)
    is_magic_attack = weapon.get("is_magic", False) or "magic" in weapon_name
    
    # Check weapon material immunities (Ghosts, Wraiths, Vampires, Liches, Atronachs require Silver/Magic)
    target_immunities = monster_data.get("immunities", [])
    immune = False
    if "normal_weapons" in target_immunities and not is_magic_attack:
        if weapon_material not in ["silver", "elven", "dwarven", "mithril", "ebony", "daedric", "glass"]:
            immune = True
            
    if hit and not immune:
        # 1. Determine authentic weapon base damage range
        matched_range = None
        for w_key, (w_min, w_max) in ARENA_WEAPONS.items():
            if w_key in weapon_name:
                matched_range = (w_min, w_max)
                break
        
        if matched_range:
            w_min, w_max = matched_range
            base_dmg = random.randint(w_min, w_max)
        else:
            # Fallback to tier dice if specific weapon name not recognized
            tier_dice = {
                1: (1, 6),   # Dagger / Fists
                2: (2, 8),   # Shortsword / Mace
                3: (3, 12),  # Broadsword / War Axe
                4: (3, 16),  # Claymore / Battleaxe
                5: (4, 20)   # Artifact / Masterwork
            }
            d_min, d_max = tier_dice.get(weapon_tier, (1, 6))
            base_dmg = random.randint(d_min, d_max)

        # 2. Apply Material Multiplier
        mat_mult = MATERIAL_MULTIPLIERS.get(weapon_material, 1.0)
        base_dmg = max(1, int(round(base_dmg * mat_mult)))

        # 3. Apply Strength Damage Bonus (Arena formula)
        str_val = attacker.get("strength", 50) if attr_name == "strength" else 50
        str_bonus = calculate_damage_bonus(str_val)
        
        # 4. Degree of Success Scaling for narrative combat
        if degree == "critical":
            damage_narrative = "critical strike"
            damage_dealt = (base_dmg * 2) + str_bonus + 2
        elif margin <= 2:
            damage_narrative = "graze"
            damage_dealt = max(1, (base_dmg // 2) + (str_bonus // 2))
        elif margin <= 5:
            damage_narrative = "solid hit"
            damage_dealt = base_dmg + str_bonus
        else:
            damage_narrative = "devastating blow"
            damage_dealt = base_dmg + str_bonus + random.randint(2, 4)
            
        # Monster on-hit status effects (when monster attacks player)
        special_traits = monster_data.get("special_traits", [])
        for trait in special_traits:
            t = trait.lower()
            if "disease" in t or "rabies" in t or "rot" in t:
                chance = 0.20
                if "chance_" in t:
                    try: chance = int(t.split("chance_")[1]) / 100.0
                    except: pass
                if random.random() < chance:
                    status_effect = "diseased"
                    break
            elif "poison" in t or "venom" in t:
                chance = 0.25
                if "bite_" in t:
                    try: chance = int(t.split("bite_")[1]) / 100.0
                    except: pass
                elif "venom_" in t:
                    try: chance = int(t.split("venom_")[1]) / 100.0
                    except: pass
                elif "chance_" in t:
                    try: chance = int(t.split("chance_")[1]) / 100.0
                    except: pass
                if random.random() < chance:
                    status_effect = "poisoned"
                    break
            elif "paralysis" in t or "paralyze" in t:
                chance = 0.25
                if "hit_" in t:
                    try: chance = int(t.split("hit_")[1]) / 100.0
                    except: pass
                elif "chance_" in t:
                    try: chance = int(t.split("chance_")[1]) / 100.0
                    except: pass
                if random.random() < chance:
                    status_effect = "paralysed"
                    break

        # Apply incoming and outgoing difficulty scaling (default 1.0)
        inc_mult = float(os.getenv("INCOMING_DAMAGE_MULTIPLIER", "1.0"))
        out_mult = float(os.getenv("OUTGOING_DAMAGE_MULTIPLIER", "1.0"))
        
        is_player_target = target.get("is_player", False) or target_name.lower() in ["player", "user", "{{user}}", "dovres malven", "eternal champion"] or not attacker.get("is_player", False)
        mult = inc_mult if is_player_target else out_mult
        damage_dealt = max(1, int(round(damage_dealt * mult)))

        if is_player_target and status_effect:
            try:
                from core.character import load_character, save_character, add_effect, add_condition
                sheet = load_character(target_name)
                add_condition(sheet, status_effect)
                add_effect(sheet, {"name": status_effect.capitalize(), "duration_turns": 5, "source": f"{target_name}"})
                save_character(target_name, sheet)
            except Exception as e:
                print(f"[roll_combat] Error applying status effect to character sheet: {e}", flush=True)

    elif hit and immune:
        damage_narrative = "ineffective (weapon passed through harmlessly)"
        damage_dealt = 0

    # Calculate Monster HP reduction if applicable
    monster_max_hp = target.get("hp_max") or monster_data.get("hp_max", 15)
    monster_current_hp = target.get("hp_current", monster_max_hp)
    remaining_hp = max(0, monster_current_hp - damage_dealt) if hit else monster_current_hp
    defeated = remaining_hp == 0 if (hit and not immune) else False
    
    return {
        "attack_roll": attack_res,
        "defense_dc": defense_dc,
        "hit": hit,
        "immune": immune,
        "damage_dealt": damage_dealt,
        "damage_tier": weapon_tier if hit else 0,
        "damage_narrative": damage_narrative,
        "status_effect": status_effect,
        "target_name": target_name,
        "target_hp_current": remaining_hp,
        "target_hp_max": monster_max_hp,
        "defeated": defeated,
        "xp_reward": monster_data.get("xp_reward", 20) if defeated else 0,
        "loot": monster_data.get("loot", []) if defeated else []
    }

def roll_initiative(combatants: list) -> list:
    """
    Takes a list of combatant dicts and returns the list sorted by initiative.
    """
    results = []
    for combatant in combatants:
        speed = combatant.get("speed", 50)
        modifier = get_modifier(speed)
        roll = random.randint(1, 20)
        total = roll + modifier
        results.append({
            "name": combatant.get("name", "Unknown"),
            "initiative_roll": roll,
            "initiative_modifier": modifier,
            "total": total
        })
    results.sort(key=lambda x: x["total"], reverse=True)
    return results

def roll_skill(skill_name: str, attribute_name: str, attribute_value: int, dc: int) -> dict:
    """
    General skill check.
    """
    res = roll_check(attribute_name, attribute_value, dc)
    res["skill_name"] = skill_name
    return res

def sorcerer_absorb(intelligence: int, willpower: int, incoming_spell_tier: int) -> dict:
    """
    Sorcerer's passive spell absorption.
    """
    absorption_chance = min((intelligence + willpower) / 2, 75)
    roll = random.randint(1, 100)
    absorbed = roll <= absorption_chance
    return {
        "absorption_chance": absorption_chance,
        "roll": roll,
        "absorbed": absorbed,
        "spell_tier": incoming_spell_tier
    }

def request_skill_check(skill_name: str, attribute_name: str, dc: int, reason: str = "") -> dict:
    """
    Structures a skill check request for the player character.
    """
    return {
        "status": "skill_check_required",
        "skill_name": str(skill_name).strip(),
        "attribute_name": str(attribute_name).strip(),
        "dc": int(dc),
        "reason": str(reason).strip()
    }

