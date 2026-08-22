"""
spellmaker.py — Narrative Mages Guild Spell Creation Engine for LM-Arena

Combines creative spell crafting with canonical Arena magical disciplines and cost formulas.
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PARSED_DIR = BASE_DIR / "utils" / "arena_parser" / "output"

SPELL_SCHOOLS = {
    "Destruction": "Spells that harm or destroy matter and energy (Fire, Frost, Shock, Pure Magic damage).",
    "Restoration": "Spells that heal wounds, cure diseases/poisons, or fortify physical attributes.",
    "Illusion": "Spells that alter perception, minds, and light (Invisibility, Chameleon, Fear, Charm).",
    "Alteration": "Spells that manipulate the physical world and its laws (Levitate, Shield, Open locks, Water Walking).",
    "Thaumaturgy": "Spells that manipulate planar probability and spacetime (Teleportation, Recall, Force).",
    "Mysticism": "Spells that alter the nature of magic itself (Spell Absorption, Dispel, Detect, Soul Trap).",
    "Conjuration": "Spells that bind daedric spirits, elemental beings, or conjure ethereal armaments.",
    "Sorcery": "Metamagic, spell reflection, and arcane amplification."
}

TARGET_TYPES = {
    "Self": {"name": "Caster Only", "cost_multiplier": 1.0, "description": "Affects only the spellcaster."},
    "Touch": {"name": "Melee Touch", "cost_multiplier": 1.0, "description": "Discharged through physical contact."},
    "Target": {"name": "Ranged Projectile", "cost_multiplier": 1.5, "description": "Hurls a bolt or projectile toward a distant target."},
    "Area": {"name": "Explosive Radius", "cost_multiplier": 2.0, "description": "Detonates across a wide area affecting all targets in radius."}
}

SPELL_TIERS = {
    1: {"name": "Novice", "base_sp": 10, "base_dc": 8, "gold_multiplier": 20, "description": "Simple cantrips and minor utility spells."},
    2: {"name": "Apprentice", "base_sp": 25, "base_dc": 11, "gold_multiplier": 35, "description": "Standard combat and survival spells."},
    3: {"name": "Journeyman", "base_sp": 45, "base_dc": 14, "gold_multiplier": 60, "description": "Potent elemental bursts and major enchantments."},
    4: {"name": "Expert", "base_sp": 75, "base_dc": 17, "gold_multiplier": 100, "description": "Master-level destruction and high warding."},
    5: {"name": "Master", "base_sp": 120, "base_dc": 20, "gold_multiplier": 180, "description": "Devastating cataclysms and legendary planar alterations."}
}

def get_school_for_effect(effect_description: str) -> str:
    """Infers the most appropriate magical school from an effect description."""
    desc = effect_description.lower()
    
    if any(k in desc for k in ["fire", "frost", "shock", "lightning", "flame", "ice", "burn", "damage", "blast", "rend", "strike"]):
        return "Destruction"
    if any(k in desc for k in ["heal", "cure", "remedy", "restore", "fortify", "stamina", "vitality", "regenerate"]):
        return "Restoration"
    if any(k in desc for k in ["invisib", "chameleon", "shadow", "fear", "terror", "blind", "charm", "illusion", "light", "glow"]):
        return "Illusion"
    if any(k in desc for k in ["levitate", "fly", "float", "open", "lock", "shield", "armor", "feather", "burden", "water walk", "breathe"]):
        return "Alteration"
    if any(k in desc for k in ["teleport", "portal", "mark", "recall", "passwall", "step"]):
        return "Thaumaturgy"
    if any(k in desc for k in ["soul", "dispel", "detect", "absorb", "magic", "silence", "mana"]):
        return "Mysticism"
    if any(k in desc for k in ["summon", "daedra", "bound", "familiar", "atronach", "raise"]):
        return "Conjuration"
    if any(k in desc for k in ["reflect", "metamagic"]):
        return "Sorcery"
        
    return "Destruction"

def create_spell(
    name: str,
    effect_description: str,
    school: str = None,
    target_type: str = "Target",
    tier: int = 2,
    caster_intelligence: int = 50
) -> dict:
    """
    Creates a new custom spell tailored for narrative gameplay.
    Calculates authentic SP costs, casting DCs, and Mages Guild creation fees.
    """
    school = school or get_school_for_effect(effect_description)
    if school not in SPELL_SCHOOLS:
        school = "Destruction"
        
    target_info = TARGET_TYPES.get(target_type, TARGET_TYPES["Target"])
    tier_info = SPELL_TIERS.get(tier, SPELL_TIERS[2])
    
    # Calculate Sp Cost and Gold creation fee
    raw_sp = tier_info["base_sp"] * target_info["cost_multiplier"]
    sp_cost = max(5, int(round(raw_sp)))
    
    gold_fee = int(sp_cost * tier_info["gold_multiplier"] / 2)
    
    # Casting DC mod by caster INT
    int_mod = (caster_intelligence - 50) // 10
    casting_dc = max(5, tier_info["base_dc"] - int_mod)
    
    return {
        "name": name.strip(),
        "school": school,
        "tier": tier,
        "tier_name": tier_info["name"],
        "target_type": target_type,
        "sp_cost": sp_cost,
        "gold_fee": gold_fee,
        "casting_dc": casting_dc,
        "effect_description": effect_description.strip(),
        "school_description": SPELL_SCHOOLS.get(school, "")
    }

evaluate_spell = create_spell
