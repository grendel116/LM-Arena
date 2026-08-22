"""
engine/character.py
Character sheet management for LM-Arena.
Reads/writes variables/saves/<character_name>/character_sheet.json.
All mutation functions return the updated sheet — callers must save explicitly.
"""

import json
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAVES_DIR = BASE_DIR / "variables" / "saves"


# ── I/O ──────────────────────────────────────────────────────────────────────

DEFAULT_SHEET = {
    "name": "Eternal Champion",
    "race": "Nord",
    "gender": "Male",
    "class": "Mage",
    "level": 1,
    "experience": 0,
    "attributes": {
        "strength": 50,
        "intelligence": 65,
        "willpower": 65,
        "agility": 50,
        "speed": 50,
        "endurance": 50,
        "personality": 50,
        "luck": 50
    },
    "derived": {
        "hp_current": 30,
        "hp_max": 30,
        "mp_current": 162,
        "mp_max": 162,
        "stamina_current": 60,
        "stamina_max": 60,
        "armor_rating": 0
    },
    "skills": {
        "destruction": 35,
        "mysticism": 30,
        "alteration": 25,
        "illusion": 20,
        "restoration": 25,
        "long_blade": 15,
        "mercantile": 15,
        "stealth": 15,
        "lockpicking": 10,
        "athletics": 20
    },
    "gold": 0,
    "inventory": [
        { "name": "Prison Rags", "type": "armor", "equipped": True }
    ],
    "spells": [
        { "name": "Spark", "school": "Destruction", "tier": 1, "mp_cost": 4 }
    ],
    "active_effects": [],
    "conditions": []
}

def load_character(save_id: str = None) -> dict:
    """Load and return the character sheet for the active save slot."""
    try:
        from core.save_manager import get_active_save_id, read_save
        slot = save_id or get_active_save_id()
        bundle = read_save(slot)
        sheet = bundle.get("character", {})
        if not sheet:
            import copy
            sheet = copy.deepcopy(DEFAULT_SHEET)
            save_character(sheet, slot)
            return sheet

        # Seamless migration: SP -> MP and Stamina
        d = sheet.setdefault("derived", {})
        if "sp_current" in d and "mp_current" not in d:
            d["mp_current"] = d.pop("sp_current")
            d["mp_max"] = d.pop("sp_max", 42)
        if "stamina_current" not in d:
            endurance = sheet.get("attributes", {}).get("endurance", 50)
            strength = sheet.get("attributes", {}).get("strength", 50)
            stamina_val = int((endurance + strength) * 0.6)
            d["stamina_current"] = stamina_val
            d["stamina_max"] = stamina_val
        return sheet
    except Exception:
        import copy
        return copy.deepcopy(DEFAULT_SHEET)


def save_character(arg1=None, arg2=None) -> None:
    """Persist the character sheet to the active save file."""
    try:
        from core.save_manager import get_active_save_id, read_save, write_save
        if isinstance(arg1, dict):
            sheet = arg1
            slot = arg2 or get_active_save_id()
        else:
            slot = arg1 or get_active_save_id()
            sheet = arg2 or {}
            
        bundle = read_save(slot)
        bundle["character"] = sheet
        write_save(slot, bundle)
    except Exception as e:
        print(f"[save_character] Error persisting character sheet: {e}")


# ── Equipment Slots & Categorization ──────────────────────────────────────────

EQUIP_SLOTS = {
    "weapon": "main_hand",
    "shield": "off_hand",
    "torch": "off_hand",
    "light": "off_hand",
    "tool": "off_hand",
    "armor": "body",
    "robes": "body",
    "head": "head",
    "helmet": "head",
    "hood": "head",
    "circlet": "head",
    "hands": "hands",
    "gauntlets": "hands",
    "gloves": "hands",
    "feet": "feet",
    "boots": "feet",
    "shoes": "feet",
    "neck": "neck",
    "amulet": "neck",
    "necklace": "neck",
    "ring": "ring",
    "cloak": "back",
    "cape": "back",
    "mantle": "back",
    "back": "back"
}

TWO_HANDED_KEYWORDS = [
    "claymore", "greatsword", "battleaxe", "warhammer", 
    "quarterstaff", "staff", "bow", "crossbow", "halberd", "two-handed", "2h"
]

def is_two_handed_item(item: dict) -> bool:
    """Check if item is a two-handed weapon."""
    if item.get("two_handed") is True or item.get("slot") in ["two_handed", "both_hands"]:
        return True
    name = item.get("name", "").lower()
    item_type = item.get("type", "").lower()
    if item_type in ["2h_weapon", "two_handed"]:
        return True
    return any(k in name for k in TWO_HANDED_KEYWORDS)

def get_item_category(item: dict) -> str:
    """Determine the equip category/slot for an item."""
    name = item.get("name", "").lower()
    item_type = item.get("type", "").lower()
    
    if item_type in ["cloak", "cape", "mantle", "back"] or any(c in name for c in ["cloak", "cape", "mantle"]):
        return "back"

    explicit_slot = item.get("slot") or item.get("equipped_slot")
    if explicit_slot:
        return explicit_slot.lower()
        
    if item_type in ["torch", "light"] or "torch" in name or "lantern" in name:
        return "torch"
    if item_type == "shield" or any(s in name for s in ["shield", "targe", "buckler"]):
        return "shield"
    if item_type in ["feet", "boots", "shoes"] or any(b in name for b in ["boot", "shoe", "greave", "sandal", "sabaton", "footwear", "slipper"]):
        return "feet"
    if item_type in ["head", "helmet", "hood"] or any(h in name for h in ["helm", "helmet", "hood", "circlet", "cap", "crown", "cowl", "coif", "diadem", "mask", "visor", "tiara"]):
        return "head"
    if item_type in ["hands", "gauntlets", "gloves"] or any(g in name for g in ["gauntlet", "glove", "bracer", "mitt", "vambrace", "handwrap"]):
        return "hands"
    if item_type in ["neck", "amulet"] or any(n in name for n in ["amulet", "necklace", "pendant", "talisman", "choker"]):
        return "neck"
    if item_type in ["ring"] or "ring" in name:
        return "ring"
    if item_type in ["weapon", "2h_weapon", "1h_weapon"] or any(w in name for w in ["dagger", "sword", "blade", "mace", "axe", "staff", "bow", "hammer", "halberd", "spear", "club", "wand", "katana", "scimitar"]):
        return "weapon"
    if item_type in ["body", "chest", "torso", "cuirass", "robes", "apparel"] or any(a in name for a in ["robe", "cuirass", "mail", "tunic", "hauberk", "breastplate", "doublet", "vest", "jerkin", "chestpiece", "rags", "clothes", "clothing", "harness", "gambeson"]):
        return "armor"
    if item_type == "armor" or "armor" in name:
        return "armor"
    return EQUIP_SLOTS.get(item_type, "")

# ── Encumbrance & Weight ──────────────────────────────────────────────────────

def get_item_weight(item: dict) -> float:
    """Returns weight in kg for an item."""
    if not item or not isinstance(item, dict):
        return 1.0
    if "weight" in item and item["weight"] is not None:
        try:
            return float(item["weight"])
        except Exception:
            pass
    name = str(item.get("name", "")).lower()
    cat = get_item_category(item)
    if "2h" in str(item.get("type", "")).lower() or any(w in name for w in ["claymore", "battleaxe", "warhammer", "greatsword", "halberd"]):
        return 8.0
    if cat == "weapon":
        return 3.0 if "dagger" not in name else 1.0
    if cat == "armor":
        if any(r in name for r in ["rags", "cloth", "robe", "tunic", "shirt"]):
            return 1.0
        if any(h in name for h in ["plate", "ebony", "iron", "steel", "daedric"]):
            return 15.0
        return 6.0
    if cat == "shield":
        return 4.0
    if cat in ["head", "feet", "hands"]:
        return 2.0
    if cat in ["ring", "neck"]:
        return 0.1
    if any(p in name for p in ["potion", "scroll", "food", "bread", "apple", "meat", "torch"]):
        return 0.5
    if any(k in name for k in ["key", "lockpick", "gem", "ruby"]):
        return 0.1
    return 1.0

def calculate_inventory_weight(inventory: list) -> float:
    """Calculates total weight of carried inventory."""
    if not inventory or not isinstance(inventory, list):
        return 0.0
    total = 0.0
    for it in inventory:
        if isinstance(it, dict):
            qty = it.get("quantity", 1)
            total += get_item_weight(it) * (int(qty) if qty and str(qty).isdigit() else 1)
    return round(total, 1)

def calculate_max_encumbrance(sheet: dict) -> float:
    """Calculates max carry capacity from strength (Strength * 2.0 kg)."""
    attrs = sheet.get("attributes", {})
    str_val = attrs.get("strength", 50)
    return round(float(str_val) * 2.0, 1)

def calculate_armor_rating(sheet: dict) -> int:
    """
    Calculates total Armor Rating (AC) from all equipped items and agility modifier.
    Arena base unarmored AC starts at 0, improved by equipped armor, shields, and material modifiers.
    """
    if not sheet:
        return 0
    attrs = sheet.get("attributes", {})
    agility = attrs.get("agility", 50)
    agil_mod = max(-5, min(10, (agility - 50) // 10))
    
    total_ac = max(0, agil_mod)
    
    for item in sheet.get("inventory", []):
        if not item.get("equipped"):
            continue
        name = item.get("name", "").lower()
        cat = get_item_category(item)
        
        # Check material bonus
        mat_bonus = 0
        for mat, bonus in [("ebony", 5), ("adamantium", 4), ("mithril", 3), ("dwarven", 2), ("elven", 1)]:
            if mat in name:
                mat_bonus = bonus
                break
                
        # Armor piece values
        if cat in ["armor", "body"]:
            if any(p in name for p in ["plate", "cuirass", "breastplate", "carapace"]):
                total_ac += 6 + mat_bonus
            elif any(c in name for c in ["chain", "hauberk", "ringmail", "mail"]):
                total_ac += 4 + (mat_bonus // 2)
            elif any(l in name for l in ["leather", "hide", "studded"]):
                total_ac += 2
            elif any(r in name for r in ["robes", "tunic", "rags", "cloth"]):
                total_ac += 0
            else:
                total_ac += 3 + mat_bonus
        elif cat == "head":
            base = 3 if any(h in name for h in ["plate", "helm", "helmet"]) else (2 if any(c in name for c in ["chain", "coif"]) else 1)
            total_ac += base + mat_bonus
        elif cat in ["shoulders", "pauldron", "pauldrons"]:
            base = 4 if "plate" in name else (2 if "chain" in name else 1)
            total_ac += base + mat_bonus
        elif cat == "hands":
            base = 2 if any(g in name for g in ["plate", "gauntlet"]) else 1
            total_ac += base + mat_bonus
        elif cat in ["legs", "greaves"]:
            base = 4 if any(p in name for p in ["plate", "greave"]) else (2.5 if "chain" in name else 1)
            total_ac += int(base) + mat_bonus
        elif cat in ["feet", "boots"]:
            base = 2 if any(b in name for b in ["plate", "sabaton", "boot"]) else 1
            total_ac += base + mat_bonus
        elif cat == "shield":
            if "tower" in name:
                total_ac += 4 + mat_bonus
            elif "kite" in name:
                total_ac += 3 + mat_bonus
            elif "round" in name:
                total_ac += 2 + mat_bonus
            elif "buckler" in name:
                total_ac += 1 + mat_bonus
            else:
                total_ac += 2 + mat_bonus
        elif cat in ["ring", "neck"]:
            if any(w in name for w in ["armor", "protection", "ward", "shielding"]):
                total_ac += 2

    return int(total_ac)

def recalculate_derived_stats(sheet: dict) -> dict:
    """Updates encumbrance, carried weight, and armor rating based on inventory state."""
    if not sheet:
        return sheet
    d = sheet.setdefault("derived", {})
    max_enc = calculate_max_encumbrance(sheet)
    cur_enc = calculate_inventory_weight(sheet.get("inventory", []))
    d["encumbrance_max"] = max_enc
    d["encumbrance_current"] = cur_enc
    d["is_encumbered"] = cur_enc > max_enc
    d["armor_rating"] = calculate_armor_rating(sheet)
    return sheet

# ── Context injection ─────────────────────────────────────────────────────────

def get_character_context(sheet: dict) -> str:
    """
    Return a compact one-block string injected into the system prompt each turn.
    Keeps token cost low while giving the LLM accurate mechanical state and full inventory.
    """
    d = sheet.get("derived", {})
    equipped_parts = []
    inv_parts = []
    for i in sheet.get("inventory", []):
        qty = i.get("quantity", 1)
        qty_str = f" x{qty}" if qty > 1 else ""
        wt = get_item_weight(i)
        wt_str = f" ({wt} kg)"
        if i.get("equipped"):
            slot = i.get("equipped_slot", "").replace("_", " ").title()
            slot_str = f" [{slot}]" if slot else ""
            equipped_parts.append(f"{i['name']}{qty_str}{slot_str}")
        inv_parts.append(f"{i['name']}{qty_str}{wt_str}")
            
    effects = [e["name"] for e in sheet.get("active_effects", [])] or ["none"]
    conditions = sheet.get("conditions", []) or ["none"]
    spells = [s["name"] for s in sheet.get("spells", [])]

    mp_cur = d.get("mp_current", d.get("sp_current", 42))
    mp_max = d.get("mp_max", d.get("sp_max", 42))
    stm_cur = d.get("stamina_current", 50)
    stm_max = d.get("stamina_max", 50)

    cur_enc = round(calculate_inventory_weight(sheet.get("inventory", [])), 1)
    max_enc = calculate_max_encumbrance(sheet)
    enc_status = "Encumbered (Slowed)" if cur_enc > max_enc else "Light"

    return (
        f"[CHARACTER STATUS]\n"
        f"Name: {sheet.get('name', 'Eternal Champion')} | {sheet.get('race', 'Nord')} {sheet.get('class', 'Mage')} | Level {sheet.get('level', 1)}\n"
        f"Vitals: HP {d.get('hp_current', 28)}/{d.get('hp_max', 28)} | MP {mp_cur}/{mp_max} | Stamina {stm_cur}/{stm_max} | Armor {d.get('armor_rating', 4)} | Gold {sheet.get('gold', 0)}\n"
        f"Encumbrance: {cur_enc}/{max_enc} kg ({enc_status})\n"
        f"Equipped: {', '.join(equipped_parts) or 'none'}\n"
        f"Carried Inventory: {', '.join(inv_parts) or 'empty'}\n"
        f"(Track changes: [arena_add_item] gained, [arena_remove_item] lost/given/used.)\n"
        f"Spells: {', '.join(spells) or 'none'}\n"
        f"Active Effects: {', '.join(effects)} | Conditions: {', '.join(conditions)}"
    )



# ── Vitals & Resource Restoration ─────────────────────────────────────────────

def take_damage(sheet: dict, amount: int) -> dict:
    """Reduce current HP. Returns updated sheet (hp_current may reach 0)."""
    sheet["derived"]["hp_current"] = max(0, sheet["derived"]["hp_current"] - amount)
    return sheet


def heal(sheet: dict, amount: int) -> dict:
    """Restore HP up to hp_max."""
    d = sheet["derived"]
    d["hp_current"] = min(d["hp_max"], d["hp_current"] + amount)
    return sheet


def spend_magicka(sheet: dict, amount: int) -> tuple[dict, bool]:
    """
    Spend MP (Magicka). Returns (updated_sheet, success).
    Returns False if insufficient MP — spell fails.
    """
    d = sheet["derived"]
    cur_mp = d.get("mp_current", d.get("sp_current", 0))
    if cur_mp < amount:
        return sheet, False
    d["mp_current"] = cur_mp - amount
    return sheet, True

def spend_spell_points(sheet: dict, amount: int) -> tuple[dict, bool]:
    """Backwards compatibility alias for spend_magicka."""
    return spend_magicka(sheet, amount)


def restore_magicka(sheet: dict, amount: int) -> dict:
    """Restore MP up to mp_max."""
    d = sheet["derived"]
    max_mp = d.get("mp_max", d.get("sp_max", 42))
    cur_mp = d.get("mp_current", d.get("sp_current", 0))
    d["mp_current"] = min(max_mp, cur_mp + amount)
    return sheet

def restore_spell_points(sheet: dict, amount: int) -> dict:
    """Backwards compatibility alias for restore_magicka."""
    return restore_magicka(sheet, amount)


def spend_stamina(sheet: dict, amount: int) -> tuple[dict, bool]:
    """
    Spend Stamina (running, power attacks, dodging).
    Stamina can reach 0 (exhaustion).
    """
    d = sheet["derived"]
    cur_stm = d.get("stamina_current", 50)
    d["stamina_current"] = max(0, cur_stm - amount)
    return sheet, d["stamina_current"] > 0


def restore_stamina(sheet: dict, amount: int) -> dict:
    """Restore Stamina up to stamina_max."""
    d = sheet["derived"]
    max_stm = d.get("stamina_max", 50)
    cur_stm = d.get("stamina_current", 0)
    d["stamina_current"] = min(max_stm, cur_stm + amount)
    return sheet


def rest(sheet: dict, hours: int = 8, safe: bool = True) -> tuple[dict, str]:
    """
    Restore resources through rest/sleep:
    - Safe rest (Inn, Camp with guard): Restores Stamina to 100%, HP to 100%, and MP to 100% (unless Sorcerer).
    - Unsafe/Short rest: Restores Stamina to 100%, HP +30%, MP +30% (unless Sorcerer).
    - Sorcerers cannot regenerate MP through rest (they rely on Spell Absorption).
    """
    d = sheet["derived"]
    is_sorcerer = sheet.get("class", "").lower() == "sorcerer"
    
    # Stamina always recovers rapidly with rest
    d["stamina_current"] = d.get("stamina_max", 50)
    
    if safe and hours >= 6:
        d["hp_current"] = d.get("hp_max", 28)
        if not is_sorcerer:
            d["mp_current"] = d.get("mp_max", 42)
        summary = "Rested fully. Health, Stamina, and Magicka restored to maximum." if not is_sorcerer else "Rested fully. Health and Stamina restored (Sorcerers do not regain Magicka through rest)."
    else:
        # Partial recovery
        hp_heal = max(4, int(d.get("hp_max", 28) * 0.35))
        d["hp_current"] = min(d.get("hp_max", 28), d.get("hp_current", 0) + hp_heal)
        if not is_sorcerer:
            mp_heal = max(5, int(d.get("mp_max", 42) * 0.35))
            d["mp_current"] = min(d.get("mp_max", 42), d.get("mp_current", 0) + mp_heal)
        summary = f"Rested for {hours} hours. Stamina restored; Health +{hp_heal}."
        
    return sheet, summary


def is_dead(sheet: dict) -> bool:
    """Return True if HP has reached zero."""
    return sheet["derived"]["hp_current"] <= 0


# ── Economy ───────────────────────────────────────────────────────────────────

def add_gold(sheet: dict, amount: int) -> dict:
    sheet["gold"] += amount
    return sheet


def spend_gold(sheet: dict, amount: int) -> tuple[dict, bool]:
    """Spend gold. Returns (sheet, success). False if insufficient funds."""
    if sheet["gold"] < amount:
        return sheet, False
    sheet["gold"] -= amount
    return sheet, True


# ── Inventory & Equip Logic ───────────────────────────────────────────────────

def add_item(sheet: dict, item: dict) -> dict:
    """
    Add an item to inventory. item must have at minimum: name, type.
    Optional keys: equipped (bool), quantity (int).
    If item with same name exists, increments quantity.
    """
    for existing in sheet["inventory"]:
        if existing["name"].lower() == item["name"].lower():
            existing["quantity"] = existing.get("quantity", 1) + item.get("quantity", 1)
            return sheet
    sheet["inventory"].append(item)
    return sheet


def remove_item(sheet: dict, item_name: str, quantity: int = 1) -> tuple[dict, bool]:
    """
    Remove quantity of item. Returns (sheet, success).
    Removes entry entirely when quantity reaches zero.
    """
    for i, item in enumerate(sheet["inventory"]):
        if item["name"].lower() == item_name.lower():
            if "quantity" in item:
                if item["quantity"] <= quantity:
                    sheet["inventory"].pop(i)
                else:
                    item["quantity"] -= quantity
            else:
                sheet["inventory"].pop(i)
            return sheet, True
    return sheet, False


def reconcile_inventory_from_turn(sheet: dict, user_text: str, follower_text: str) -> tuple[dict, list[dict]]:
    """
    Reconciles character inventory against the context of the turn.
    Detects if the player explicitly discarded, consumed, or surrendered an item currently held.
    Returns (updated_sheet, list_of_removed_items).
    """
    if not sheet or "inventory" not in sheet or not sheet["inventory"]:
        return sheet, []

    combined_text = f"{user_text}\n{follower_text}"
    if not combined_text.strip():
        return sheet, []

    removals = []
    
    negation_patterns = [
        r'\b(?:not|never|without|refuse\w*|hesitat\w*)\s+(?:to\s+)?(?:drop|discard|leave|lose|release|toss)\b',
        r'\b(?:holding|gripping|grasping|clutching|brandishing)\s+(?:the|my|a|an)?\s*',
        r'\b(?:held|gripped|grasped|clutched)\s+(?:high|tight|fast|close|firmly)\b'
    ]

    relinquish_actions = [
        r'(?:\bleaving\s+(?:my|the|this|a)?\s*)',
        r'(?:\bleft\s+(?:my|the|this|a)?\s*)',
        r'(?:\bdrop(?:ped|ping|s)?\s+(?:my|the|this|a)?\s*)',
        r'(?:\bdiscard(?:ed|ing|s)?\s+(?:my|the|this|a)?\s*)',
        r'(?:\btoss(?:ed|ing|es)?\s+(?:away|down|aside)?\s*(?:my|the|this|a)?\s*)',
        r'(?:\bthrew\s+(?:away|down|aside)?\s*(?:my|the|this|a)?\s*)',
        r'(?:\bthrow(?:ing|s)?\s+(?:away|down|aside)?\s*(?:my|the|this|a)?\s*)',
        r'(?:\bset(?:ting)?\s+down\s+(?:my|the|this|a)?\s*)',
        r'(?:\bplaced?\s+(?:my|the|this|a)?\s*)',
        r'(?:\bsurrender(?:ed|ing|s)?\s+(?:my|the|this|a)?\s*)',
        r'(?:\bdrink(?:ing|s)?\s+(?:my|the|this|a)?\s*)',
        r'(?:\bdrank\s+(?:my|the|this|a)?\s*)',
        r'(?:\bswallow(?:ed|ing|s)?\s+(?:my|the|this|a)?\s*)',
        r'(?:\bconsum(?:ed|ing|es)?\s+(?:my|the|this|a)?\s*)',
        r'(?:\bused\s+up\s+(?:my|the|this|a)?\s*)',
    ]

    items_to_remove = []

    for item in list(sheet["inventory"]):
        item_name = item.get("name", "").strip()
        if not item_name:
            continue

        item_escaped = re.escape(item_name)
        
        found_relinquish = False
        for action_pat in relinquish_actions:
            full_pattern = rf'{action_pat}{item_escaped}\b'
            matches = list(re.finditer(full_pattern, user_text, re.IGNORECASE))
            if not matches:
                matches = list(re.finditer(full_pattern, follower_text, re.IGNORECASE))
                
            for match in matches:
                start_pos = max(0, match.start() - 40)
                snippet = combined_text[start_pos:match.end()]
                is_negated = any(re.search(neg, snippet, re.IGNORECASE) for neg in negation_patterns)
                if not is_negated:
                    found_relinquish = True
                    break
            if found_relinquish:
                break

        if found_relinquish:
            items_to_remove.append(item_name)

    for it_name in items_to_remove:
        sheet, success = remove_item(sheet, it_name, 1)
        if success:
            removals.append({"name": it_name, "quantity": 1})
            print(f"[Inventory Reconciliation] Automatically reconciled dropped item: {it_name}", flush=True)

    if removals:
        recalculate_derived_stats(sheet)

    return sheet, removals


def equip_item(sheet: dict, item_name: str) -> tuple[dict, bool]:
    """
    Equip an item by name enforcing slot constraints:
    - 2 Hand rule: 1H weapons can dual wield (Main + Off), 2H weapon occupies both hands.
    - Shield/Torch occupies Off Hand (unequips 2H weapon).
    - Body Armor / Head / Hands / Feet / Amulet: max 1.
    - Ring: max 2.
    """
    target_item = None
    for item in sheet["inventory"]:
        if item["name"].lower() == item_name.lower():
            target_item = item
            break
            
    if not target_item:
        return sheet, False
        
    category = get_item_category(target_item)
    if not category:
        return sheet, False

    two_handed = is_two_handed_item(target_item)

    # 1. Weapon / 2H Weapon Handling
    if category == "weapon":
        if two_handed:
            # Unequip all other weapons, shields, and torches
            for item in sheet["inventory"]:
                cat = get_item_category(item)
                if cat in ["weapon", "shield", "torch"]:
                    item["equipped"] = False
                    item.pop("equipped_slot", None)
            target_item["equipped"] = True
            target_item["equipped_slot"] = "both_hands"
        else:
            # 1-Handed weapon: check hand availability
            main_hand = next((i for i in sheet["inventory"] if i.get("equipped") and i.get("equipped_slot") == "main_hand"), None)
            off_hand = next((i for i in sheet["inventory"] if i.get("equipped") and i.get("equipped_slot") == "off_hand"), None)
            both_hands = next((i for i in sheet["inventory"] if i.get("equipped") and i.get("equipped_slot") == "both_hands"), None)
            
            if both_hands:
                both_hands["equipped"] = False
                both_hands.pop("equipped_slot", None)
                main_hand = None

            if not main_hand:
                target_item["equipped"] = True
                target_item["equipped_slot"] = "main_hand"
            elif not off_hand and main_hand != target_item:
                # Dual wield secondary weapon!
                target_item["equipped"] = True
                target_item["equipped_slot"] = "off_hand"
            else:
                # Replace main hand weapon
                if main_hand:
                    main_hand["equipped"] = False
                    main_hand.pop("equipped_slot", None)
                target_item["equipped"] = True
                target_item["equipped_slot"] = "main_hand"

    # 2. Shield / Torch / Tool Handling (Off Hand)
    elif category in ["shield", "torch"]:
        # Unequip any 2H weapon
        for item in sheet["inventory"]:
            if item.get("equipped") and item.get("equipped_slot") == "both_hands":
                item["equipped"] = False
                item.pop("equipped_slot", None)
        # Unequip existing off-hand item
        for item in sheet["inventory"]:
            if item.get("equipped") and item.get("equipped_slot") == "off_hand":
                item["equipped"] = False
                item.pop("equipped_slot", None)
                
        target_item["equipped"] = True
        target_item["equipped_slot"] = "off_hand"

    # 3. Body Armor
    elif category == "armor":
        for item in sheet["inventory"]:
            if item.get("equipped") and get_item_category(item) == "armor":
                item["equipped"] = False
                item.pop("equipped_slot", None)
        target_item["equipped"] = True
        target_item["equipped_slot"] = "body"

    # 4. Head / Hands / Feet / Neck / Back
    elif category in ["head", "hands", "feet", "neck", "back", "cloak"]:
        for item in sheet["inventory"]:
            if item.get("equipped") and get_item_category(item) == category:
                item["equipped"] = False
                item.pop("equipped_slot", None)
        target_item["equipped"] = True
        target_item["equipped_slot"] = "back" if category in ["cloak", "back"] else category

    # 5. Rings (Max 2)
    elif category == "ring":
        equipped_rings = [i for i in sheet["inventory"] if i.get("equipped") and get_item_category(i) == "ring"]
        if len(equipped_rings) >= 2:
            equipped_rings[0]["equipped"] = False
            equipped_rings[0].pop("equipped_slot", None)
        target_item["equipped"] = True
        target_item["equipped_slot"] = "ring"

    recalculate_derived_stats(sheet)
    return sheet, True


def unequip_item(sheet: dict, item_name: str) -> tuple[dict, bool]:
    """Mark an item as unequipped."""
    for item in sheet["inventory"]:
        if item["name"].lower() == item_name.lower():
            item["equipped"] = False
            item.pop("equipped_slot", None)
            recalculate_derived_stats(sheet)
            return sheet, True
    return sheet, False


def drop_item(sheet: dict, item_name: str, quantity: int = 1) -> tuple[dict, dict]:
    """
    Removes an item or decrements its quantity from the player's inventory.
    Returns (updated_sheet, dropped_item_dict or None).
    """
    inventory = sheet.setdefault("inventory", [])
    dropped = None
    
    for i, item in enumerate(inventory):
        if item.get("name", "").lower() == item_name.lower():
            curr_qty = item.get("quantity", 1)
            if curr_qty > quantity:
                item["quantity"] = curr_qty - quantity
                dropped = dict(item)
                dropped["quantity"] = quantity
            else:
                dropped = inventory.pop(i)
            break
            
    if dropped:
        recalculate_derived_stats(sheet)
    return sheet, dropped


# ── Spells ────────────────────────────────────────────────────────────────────

def learn_spell(sheet: dict, spell: dict) -> dict:
    """Add a spell if not already known. spell: { name, school, tier, sp_cost }."""
    names = [s["name"].lower() for s in sheet["spells"]]
    if spell["name"].lower() not in names:
        sheet["spells"].append(spell)
    return sheet


def forget_spell(sheet: dict, spell_name: str) -> dict:
    sheet["spells"] = [s for s in sheet["spells"] if s["name"].lower() != spell_name.lower()]
    return sheet


# ── Effects and conditions ────────────────────────────────────────────────────

def add_effect(sheet: dict, effect: dict) -> dict:
    """
    Add an active effect. effect: { name, duration_turns, source }.
    Replaces existing effect with same name.
    """
    sheet["active_effects"] = [e for e in sheet["active_effects"] if e["name"] != effect["name"]]
    sheet["active_effects"].append(effect)
    return sheet


def remove_effect(sheet: dict, effect_name: str) -> dict:
    sheet["active_effects"] = [e for e in sheet["active_effects"] if e["name"] != effect_name]
    return sheet


def tick_effects(sheet: dict) -> tuple[dict, list]:
    """
    Decrement duration on all effects. Remove expired ones.
    Returns (sheet, list_of_expired_effect_names).
    """
    expired = []
    remaining = []
    for e in sheet["active_effects"]:
        e["duration_turns"] -= 1
        if e["duration_turns"] <= 0:
            expired.append(e["name"])
        else:
            remaining.append(e)
    sheet["active_effects"] = remaining
    return sheet, expired


def add_condition(sheet: dict, condition: str) -> dict:
    """Add a narrative condition string (e.g. 'poisoned', 'diseased')."""
    if condition not in sheet["conditions"]:
        sheet["conditions"].append(condition)
    return sheet


def remove_condition(sheet: dict, condition: str) -> dict:
    sheet["conditions"] = [c for c in sheet["conditions"] if c != condition]
    return sheet


# ── Progression ───────────────────────────────────────────────────────────────

def add_experience(sheet: dict, amount: int) -> tuple[dict, bool]:
    """
    Add XP. Returns (sheet, leveled_up).
    Simple threshold: 100 * current_level XP per level.
    """
    sheet["experience"] += amount
    threshold = 100 * sheet["level"]
    if sheet["experience"] >= threshold:
        sheet["experience"] -= threshold
        sheet["level"] += 1
        # Increase hp_max and sp_max on level up
        sheet["derived"]["hp_max"] += 4
        sheet["derived"]["sp_max"] += 6
        return sheet, True
    return sheet, False


def get_attribute(sheet: dict, attr_name: str) -> int:
    """Return attribute value by name (case-insensitive). Returns 50 if not found."""
    return sheet["attributes"].get(attr_name.lower(), 50)


# ── Character Creation & Class Templates ──────────────────────────────────────

CLASS_TEMPLATES = {
    # Warrior Archetype
    "warrior": {"primary": ["strength", "endurance"], "hp_bonus": 12, "mp_mult": 0.5, "skills": ["long_blade", "blunt", "athletics", "armor"]},
    "knight": {"primary": ["strength", "personality"], "hp_bonus": 10, "mp_mult": 0.5, "skills": ["long_blade", "shield", "mercantile", "armor"]},
    "ranger": {"primary": ["agility", "endurance"], "hp_bonus": 8, "mp_mult": 0.8, "skills": ["archery", "stealth", "athletics", "long_blade"]},
    "archer": {"primary": ["agility", "strength"], "hp_bonus": 6, "mp_mult": 0.5, "skills": ["archery", "stealth", "dodge", "athletics"]},
    "monk": {"primary": ["agility", "willpower"], "hp_bonus": 8, "mp_mult": 0.8, "skills": ["hand_to_hand", "athletics", "dodge", "restoration"]},
    "barbarian": {"primary": ["strength", "speed"], "hp_bonus": 14, "mp_mult": 0.3, "skills": ["two_handed", "blunt", "athletics", "intimidation"]},
    
    # Mage Archetype
    "mage": {"primary": ["intelligence", "willpower"], "hp_bonus": 0, "mp_mult": 2.5, "skills": ["destruction", "mysticism", "alteration", "illusion", "restoration"]},
    "sorcerer": {"primary": ["intelligence", "endurance"], "hp_bonus": 2, "mp_mult": 3.0, "skills": ["destruction", "mysticism", "alteration", "spell_absorption"]},
    "healer": {"primary": ["willpower", "personality"], "hp_bonus": 4, "mp_mult": 2.0, "skills": ["restoration", "mysticism", "mercantile", "blunt"]},
    "battlemage": {"primary": ["intelligence", "strength"], "hp_bonus": 6, "mp_mult": 1.8, "skills": ["destruction", "long_blade", "alteration", "armor"]},
    "spellsword": {"primary": ["willpower", "agility"], "hp_bonus": 6, "mp_mult": 1.5, "skills": ["destruction", "restoration", "long_blade", "illusion"]},
    "nightblade": {"primary": ["agility", "intelligence"], "hp_bonus": 4, "mp_mult": 1.5, "skills": ["illusion", "alteration", "stealth", "short_blade"]},
    
    # Thief Archetype
    "thief": {"primary": ["agility", "speed"], "hp_bonus": 4, "mp_mult": 0.5, "skills": ["lockpicking", "stealth", "pickpocket", "short_blade"]},
    "burglar": {"primary": ["agility", "intelligence"], "hp_bonus": 4, "mp_mult": 0.6, "skills": ["lockpicking", "stealth", "athletics", "mercantile"]},
    "assassin": {"primary": ["agility", "speed"], "hp_bonus": 6, "mp_mult": 0.5, "skills": ["short_blade", "stealth", "alchemy", "archery"]},
    "rogue": {"primary": ["agility", "personality"], "hp_bonus": 6, "mp_mult": 0.8, "skills": ["long_blade", "mercantile", "lockpicking", "streetwise"]},
    "acrobat": {"primary": ["agility", "speed"], "hp_bonus": 4, "mp_mult": 0.5, "skills": ["athletics", "dodge", "hand_to_hand", "stealth"]},
    "bard": {"primary": ["personality", "intelligence"], "hp_bonus": 4, "mp_mult": 1.2, "skills": ["mercantile", "illusion", "lore", "short_blade"]}
}

RACE_BONUSES = {
    "nord": {"attributes": {"strength": 10, "endurance": 10}},
    "breton": {"attributes": {"intelligence": 10, "willpower": 10}},
    "redguard": {"attributes": {"strength": 10, "agility": 10}},
    "high elf": {"attributes": {"intelligence": 15, "willpower": 5}},
    "wood elf": {"attributes": {"agility": 15, "speed": 10}},
    "dark elf": {"attributes": {"agility": 5, "intelligence": 5, "strength": 5}},
    "khajiit": {"attributes": {"agility": 10, "speed": 10}},
    "argonian": {"attributes": {"agility": 5, "endurance": 10}},
    "imperial": {"attributes": {"personality": 10, "willpower": 5, "luck": 5}}
}

def update_character_identity(sheet: dict, name: str = None, race: str = None, gender: str = None, character_class: str = None, custom_attributes: dict = None, reset_vitals: bool = False) -> dict:
    """Updates race, class, gender, name and recalculates base attributes and derived vitals."""
    if name:
        sheet["name"] = name.strip()
    if gender:
        sheet["gender"] = gender.strip().capitalize()
    if race:
        sheet["race"] = race.strip().title()
    if character_class:
        sheet["class"] = character_class.strip().title()
        
    cls_key = sheet.get("class", "Warrior").lower()
    tmpl = CLASS_TEMPLATES.get(cls_key, CLASS_TEMPLATES["warrior"])
    
    attrs = sheet.setdefault("attributes", {
        "strength": 50, "intelligence": 50, "willpower": 50, "agility": 50,
        "speed": 50, "endurance": 50, "personality": 50, "luck": 50
    })
    
    if custom_attributes:
        for k, v in custom_attributes.items():
            if k in attrs:
                attrs[k] = int(v)
    else:
        # Base attributes at 50
        for k in attrs:
            attrs[k] = 50
            
        # Apply class primary attributes (65)
        for prim in tmpl.get("primary", []):
            if prim in attrs:
                attrs[prim] = 65
                
        # Apply race bonuses
        race_key = sheet.get("race", "Nord").lower()
        race_bonus = RACE_BONUSES.get(race_key, {})
        for attr, bonus in race_bonus.get("attributes", {}).items():
            if attr in attrs:
                attrs[attr] += bonus
                
    endurance = attrs.get("endurance", 50)
    strength = attrs.get("strength", 50)
    intelligence = attrs.get("intelligence", 50)
    
    d = sheet.setdefault("derived", {})
    hp_base = 20 + int(endurance * 0.2) + tmpl.get("hp_bonus", 4)
    d["hp_max"] = hp_base
    if reset_vitals or sheet.get("level", 1) <= 1 or "hp_current" not in d:
        d["hp_current"] = hp_base
    else:
        d["hp_current"] = min(hp_base, max(0, d["hp_current"]))
    
    mp_base = max(10, int(intelligence * tmpl.get("mp_mult", 1.0)))
    d["mp_max"] = mp_base
    if reset_vitals or sheet.get("level", 1) <= 1 or "mp_current" not in d:
        d["mp_current"] = mp_base
    else:
        d["mp_current"] = min(mp_base, max(0, d["mp_current"]))
    
    stamina_base = int((endurance + strength) * 0.6)
    d["stamina_max"] = stamina_base
    if reset_vitals or sheet.get("level", 1) <= 1 or "stamina_current" not in d:
        d["stamina_current"] = stamina_base
    else:
        d["stamina_current"] = min(stamina_base, max(0, d["stamina_current"]))
    
    # Encumbrance
    max_carry = calculate_max_encumbrance(sheet)
    curr_weight = calculate_inventory_weight(sheet.get("inventory", []))
    d["encumbrance_max"] = max_carry
    d["encumbrance_current"] = curr_weight
    d["is_encumbered"] = curr_weight > max_carry

    # Configure starting spells if empty
    if "spells" not in sheet or not sheet["spells"]:
        if cls_key in ("mage", "sorcerer", "battlemage", "spellsword", "nightblade"):
            sheet["spells"] = [{"name": "Spark", "school": "Destruction", "tier": 1, "mp_cost": 4}]
        elif cls_key == "healer":
            sheet["spells"] = [{"name": "Mend Wounds", "school": "Restoration", "tier": 1, "mp_cost": 5}]
        else:
            sheet["spells"] = []
            
    return sheet



def rollback_tool_effects(character_name: str, tool_calls: list) -> None:
    """Reverts character mutations from deleted or rolled-back turns."""
    if not tool_calls:
        return
    try:
        sheet = load_character(character_name)
        modified = False

        # Build response lookup: call_id -> parsed response string
        response_map = {}
        for tc in tool_calls:
            if isinstance(tc, dict) and tc.get("type") == "response" and tc.get("id"):
                response_map[tc["id"]] = tc.get("response", "")

        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            if tc.get("type") != "call":
                continue
            t_name = tc.get("name", "")
            args = tc.get("args", {})
            if not isinstance(args, dict):
                continue
            call_id = tc.get("id", "")

            # Extract quantity / amount using parameter aliases
            amount = 0
            for key in ("amount", "damage_amount", "damage", "heal_amount", "healing",
                        "mp_amount", "stamina_amount", "gold_amount", "xp_amount", "cost"):
                if args.get(key) is not None:
                    try:
                        amount = int(args[key])
                        break
                    except (ValueError, TypeError):
                        pass

            # Parse the matching response entry for this call
            res_dict = {}
            res_str = response_map.get(call_id, "")
            if res_str:
                try:
                    import ast
                    res_dict = ast.literal_eval(res_str) if isinstance(res_str, str) and res_str.strip().startswith("{") else {}
                except Exception:
                    try:
                        res_dict = json.loads(res_str) if isinstance(res_str, str) else {}
                    except Exception:
                        res_dict = {}

            if t_name in ("arena_spend_magicka", "arena_spend_spell_points"):
                restore_magicka(sheet, amount)
                modified = True
            elif t_name in ("arena_restore_magicka", "arena_restore_spell_points"):
                spend_magicka(sheet, amount)
                modified = True
            elif t_name == "arena_spend_stamina":
                restore_stamina(sheet, amount)
                modified = True
            elif t_name == "arena_restore_stamina":
                spend_stamina(sheet, amount)
                modified = True
            elif t_name == "arena_take_damage":
                actual_dmg = res_dict.get("damage_inflicted")
                if actual_dmg is not None:
                    actual_dmg = int(actual_dmg)
                else:
                    from core.mechanics import INCOMING_DAMAGE_MULTIPLIER
                    actual_dmg = max(1, int(round(amount * INCOMING_DAMAGE_MULTIPLIER))) if amount > 0 else 0
                heal(sheet, actual_dmg)
                modified = True
            elif t_name == "arena_roll_combat":
                if res_dict.get("damage_dealt"):
                    target_name = str(res_dict.get("target_name", "")).lower()
                    is_player = (
                        target_name in ["player", "user", character_name.lower()]
                        or res_dict.get("is_player", False)
                    )
                    dmg = int(res_dict.get("damage_dealt", 0))
                    if is_player and dmg > 0:
                        heal(sheet, dmg)
                        modified = True
            elif t_name == "arena_heal":
                take_damage(sheet, amount)
                modified = True
            elif t_name == "arena_rest":
                # Restore pre-rest vitals from the response snapshot
                d = sheet["derived"]
                if "hp_before" in res_dict:
                    d["hp_current"] = int(res_dict["hp_before"])
                    modified = True
                if "mp_before" in res_dict:
                    d["mp_current"] = int(res_dict["mp_before"])
                    modified = True
                if "stamina_before" in res_dict:
                    d["stamina_current"] = int(res_dict["stamina_before"])
                    modified = True
            elif t_name == "arena_spend_gold":
                add_gold(sheet, amount)
                modified = True
            elif t_name == "arena_add_gold":
                spend_gold(sheet, amount)
                modified = True
            elif t_name == "arena_add_item":
                item_name = args.get("item_name")
                qty = int(args.get("quantity", 1))
                if item_name:
                    remove_item(sheet, item_name, qty)
                    modified = True
            elif t_name == "arena_remove_item":
                item_name = args.get("item_name")
                qty = int(args.get("quantity", 1))
                item_type = args.get("item_type", "misc")
                if item_name:
                    add_item(sheet, {"name": item_name, "type": item_type, "quantity": qty})
                    modified = True
            elif t_name in ("arena_add_experience", "arena_add_xp"):
                if amount > 0:
                    sheet["experience"] = max(0, sheet.get("experience", 0) - amount)
                    # Revert level-up bonuses if the response indicates leveling occurred
                    if res_dict.get("leveled_up"):
                        sheet["level"] = max(1, sheet.get("level", 1) - 1)
                        sheet["derived"]["hp_max"] = max(1, sheet["derived"].get("hp_max", 28) - 4)
                        sheet["derived"]["hp_current"] = min(sheet["derived"]["hp_current"], sheet["derived"]["hp_max"])
                        if "sp_max" in sheet["derived"]:
                            sheet["derived"]["sp_max"] = max(1, sheet["derived"].get("sp_max", 42) - 6)
                    modified = True
            elif t_name == "arena_learn_spell":
                spell_name = args.get("spell_name")
                if spell_name and "spells" in sheet:
                    sheet["spells"] = [s for s in sheet["spells"] if s.get("name", "").lower() != spell_name.lower()]
                    modified = True
            elif t_name == "arena_add_effect":
                effect_name = args.get("effect_name")
                if effect_name:
                    sheet = remove_effect(sheet, effect_name)
                    modified = True
            elif t_name == "arena_remove_effect":
                effect_name = args.get("effect_name")
                if effect_name:
                    dur = int(args.get("duration_turns", 3))
                    src = args.get("source", "restored")
                    sheet = add_effect(sheet, {"name": effect_name, "duration_turns": dur, "source": src})
                    modified = True
            elif t_name in ("arena_advance_stage", "arena_set_quest_stage", "arena_set_location", "arena_travel"):
                try:
                    from core.world_engine import load_world_state, save_world_state
                    ws = load_world_state(character_name)
                    if t_name in ("arena_advance_stage", "arena_set_quest_stage"):
                        if ws.get("quest_stage", 10) > 10:
                            ws["quest_stage"] = max(10, ws["quest_stage"] - 10)
                            save_world_state(character_name, ws)
                except Exception as q_err:
                    print(f"[rollback_tool_effects] Error rolling back quest/world state: {q_err}", flush=True)

                    
        if modified:
            save_character(character_name, sheet)
    except Exception as e:
        print(f"[rollback_tool_effects] Error reverting tool effects: {e}", flush=True)
