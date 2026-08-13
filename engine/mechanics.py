import random

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
    Attack resolution for narrative combat.
    """
    attr_name = weapon.get("attribute_used", "strength")
    attr_value = attacker.get(attr_name, 50)
    
    target_agility = target.get("agility", 50)
    defense_dc = 10 + get_modifier(target_agility)
    
    attack_res = roll_check(attr_name, attr_value, defense_dc)
    hit = attack_res["success"]
    margin = attack_res["margin"]
    
    damage_narrative = "miss"
    if hit:
        if margin <= 2:
            damage_narrative = "graze"
        elif margin <= 5:
            damage_narrative = "solid hit"
        else:
            damage_narrative = "devastating blow"
            
    status_effect = None
    if hit:
        status_chance = random.random()
        if status_chance > 0.95:
            status_effect = random.choice(["poisoned", "paralysed", "diseased"])
            
    return {
        "attack_roll": attack_res,
        "defense_dc": defense_dc,
        "hit": hit,
        "damage_tier": weapon.get("damage_tier", 1) if hit else 0,
        "damage_narrative": damage_narrative,
        "status_effect": status_effect
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
