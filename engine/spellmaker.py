SPELL_SCHOOLS = {
    "Destruction": "Spells that harm or destroy matter and energy.",
    "Restoration": "Spells that heal, restore, or fortify the body and attributes.",
    "Illusion": "Spells that alter perception, mind, and light.",
    "Alteration": "Spells that manipulate the physical world and its rules.",
    "Thaumaturgy": "Spells that manipulate the laws of nature and probability temporarily.",
    "Mysticism": "Spells that alter the nature of magic itself and soul manipulation.",
    "Conjuration": "Spells that summon creatures or items from other planes.",
    "Sorcery": "Spells dealing with spell absorption and complex meta-magic."
}

SPELL_TIERS = {
    1: {"name": "Novice", "base_dc": 10, "description": "Simple spells for beginners.", "cost_modifier": 1},
    2: {"name": "Apprentice", "base_dc": 12, "description": "Standard spells for initiates.", "cost_modifier": 2},
    3: {"name": "Journeyman", "base_dc": 15, "description": "Complex spells for experienced casters.", "cost_modifier": 3},
    4: {"name": "Expert", "base_dc": 18, "description": "Powerful spells for masters.", "cost_modifier": 4},
    5: {"name": "Master", "base_dc": 22, "description": "Legendary spells for arch-mages.", "cost_modifier": 5}
}

def _get_modifier(attribute_value: int) -> int:
    """Internal helper to get modifier for spell DC calculation."""
    return round((attribute_value - 50) / 10)

def evaluate_spell(description: str, school: str, tier: int, caster_intelligence: int) -> dict:
    """Builds a spell card from the player's creative input."""
    tier_info = SPELL_TIERS.get(tier, SPELL_TIERS[1])
    casting_dc = tier_info["base_dc"] - _get_modifier(caster_intelligence)
    
    return {
        "name": description,
        "school": school,
        "tier": tier,
        "casting_dc": casting_dc,
        "tier_name": tier_info["name"],
        "school_description": SPELL_SCHOOLS.get(school, "Unknown magical discipline")
    }

def get_school_for_effect(effect_description: str) -> str:
    """Simple keyword matching to suggest a school from an effect description."""
    desc_lower = effect_description.lower()
    
    if any(k in desc_lower for k in ["fire", "frost", "shock", "damage"]):
        return "Destruction"
    if any(k in desc_lower for k in ["heal", "cure", "fortify"]):
        return "Restoration"
    if any(k in desc_lower for k in ["invisible", "fear", "charm", "light"]):
        return "Illusion"
    if any(k in desc_lower for k in ["levitate", "open", "shield", "burden"]):
        return "Alteration"
    if any(k in desc_lower for k in ["teleport", "mark", "recall"]):
        return "Thaumaturgy"
    if any(k in desc_lower for k in ["soul", "dispel", "detect", "absorb magic", "absorb"]):
        return "Mysticism"
    if any(k in desc_lower for k in ["summon", "bound", "turn undead"]):
        return "Conjuration"
    if any(k in desc_lower for k in ["reflect"]):
        return "Sorcery"
        
    return "Mysticism"
