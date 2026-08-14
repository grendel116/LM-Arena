import os
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BESTIARY_PATH = BASE_DIR / "core" / "world" / "bestiary.json"

_BESTIARY_CACHE = None

def load_bestiary() -> dict:
    global _BESTIARY_CACHE
    if _BESTIARY_CACHE is not None:
        return _BESTIARY_CACHE
    if os.path.exists(BESTIARY_PATH):
        try:
            with open(BESTIARY_PATH, "r", encoding="utf-8") as f:
                _BESTIARY_CACHE = json.load(f).get("monsters", {})
                return _BESTIARY_CACHE
        except Exception as e:
            print(f"[Bestiary] Error loading bestiary: {e}")
    return {}

def get_monster(name_or_key: str) -> dict:
    """Find a monster template by key or substring match."""
    bestiary = load_bestiary()
    if not name_or_key:
        return {}
    clean_key = name_or_key.lower().replace(" ", "_").replace("-", "_")
    if clean_key in bestiary:
        return bestiary[clean_key]
    
    # Substring search
    for k, v in bestiary.items():
        if k in clean_key or clean_key in k or v.get("name", "").lower() in name_or_key.lower():
            return v
    return {}

def get_modifier(attribute_value: int) -> int:
    """
    Returns the attribute modifier.
    Arena attributes are 0-100, centered at 50.
    """
    return round((attribute_value - 50) / 10)

def roll_check(attribute_name: str, attribute_value: int, dc: int, advantage: bool = False, disadvantage: bool = False) -> dict:
    """
    Rolls a d20 plus modifier against a DC.
    """
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
    Attack resolution with authentic Arena dice pools, weapon damage, material immunities, and monster HP tracking.
    """
    attr_name = weapon.get("attribute_used", "strength")
    attr_value = attacker.get(attr_name, 50)
    
    # Look up bestiary template if target matches a known creature
    target_name = target.get("name", "Adversary")
    monster_data = get_monster(target_name) if not target.get("is_player") else {}
    
    target_agility = target.get("agility") or monster_data.get("base_agility", 50)
    defense_dc = 10 + get_modifier(target_agility)
    
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
    
    weapon_material = weapon.get("material", "iron").lower()
    weapon_tier = weapon.get("damage_tier", 1)
    is_magic_attack = weapon.get("is_magic", False) or "magic" in weapon.get("name", "").lower()
    
    # Check weapon material immunities (Ghosts, Wraiths, Vampires, Liches, Atronachs require Silver/Magic)
    target_immunities = monster_data.get("immunities", [])
    immune = False
    if "normal_weapons" in target_immunities and not is_magic_attack:
        if weapon_material not in ["silver", "elven", "dwarven", "mithril", "ebony", "daedric", "glass"]:
            immune = True
            
    if hit and not immune:
        # Base damage dice calculation by weapon tier
        tier_dice = {
            1: (1, 4),   # Dagger / Club
            2: (1, 8),   # Shortsword / Mace
            3: (1, 10),  # Broadsword / War Axe
            4: (2, 8),   # Claymore / Battleaxe
            5: (3, 8)    # Artifact / Masterwork
        }
        num_dice, die_faces = tier_dice.get(weapon_tier, (1, 6))
        base_dmg = sum(random.randint(1, die_faces) for _ in range(num_dice))
        attr_bonus = max(0, get_modifier(attr_value))
        
        if degree == "critical":
            damage_narrative = "critical strike"
            damage_dealt = (base_dmg * 2) + attr_bonus + 2
        elif margin <= 2:
            damage_narrative = "graze"
            damage_dealt = max(1, (base_dmg // 2) + attr_bonus)
        elif margin <= 5:
            damage_narrative = "solid hit"
            damage_dealt = base_dmg + attr_bonus
        else:
            damage_narrative = "devastating blow"
            damage_dealt = base_dmg + attr_bonus + random.randint(2, 4)
            
        # Monster on-hit status effects (when monster attacks player)
        special_traits = monster_data.get("special_traits", [])
        if "paralysis_on_hit_25" in special_traits and random.random() < 0.25:
            status_effect = "paralysed"
        elif "disease_chance_15" in special_traits and random.random() < 0.15:
            status_effect = "diseased"
        elif "poison_venom_25" in special_traits and random.random() < 0.25:
            status_effect = "poisoned"
            
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
