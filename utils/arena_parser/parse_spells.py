"""
parse_spells.py — Phase 1A binary parser for SPELLS.LST

Record layout (85 bytes each, 128 records = SPELLSG general spells):
  Offset  Size  Field
  0       36    params: 6 effects x 3 uint16_le = [[p0,p1,p2], ...]
  36      1     target_type
  37      1     unknown
  38      1     element
  39      2     flags (uint16_le)
  41      3     effects[3]       — effect IDs (0xFF = empty slot)
  44      3     sub_effects[3]
  47      3     affected_attributes[3]
  50      2     cost (uint16_le)
  52      33    name (null-terminated char[33])

Source: ArenaTypes.h SpellData struct (SIZE=85, Spellsg=128 records)
"""

import json
import os
import struct

ARENA_DIR = r"c:\Users\Davy\Documents\My Games\Arena"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

RECORD_SIZE = 85
SPELLSG_COUNT = 128

# Effect ID → human-readable name (from SPELLMKR.TXT effect templates)
EFFECT_NAMES = {
    0x00: "Disease",
    0x01: "Poison",
    0x02: "Fear",
    0x03: "Paralyze",
    0x04: "Curse",
    0x05: "Instakill",
    0x06: "Damage HP over time",
    0x07: "Damage Fatigue over time",
    0x08: "Damage SP over time",
    0x09: "HP Shield",
    0x0A: "Create Wall",
    0x0B: "Create Floor",
    0x0C: "Cure Disease",
    0x0D: "Cure Poison",
    0x0E: "Dispel Magic",
    0x0F: "Fortify Attribute",
    0x10: "Damage HP instant",
    0x11: "Light",
    0x12: "Lock",
    0x13: "Open Lock",
    0x14: "Repair",
    0x15: "Silence",
    0x16: "Slow",
    0x17: "Stamina (Fortify Stamina)",
    0x18: "Teleport",
    0x19: "Invisibility",
    0x1A: "Chameleon",
    0x1B: "Charm",
    0x1C: "Levitate",
    0x1D: "Resist Element",
    0x1E: "Water Breathing",
    0x1F: "Water Walking",
    0x20: "Slowfall",
    0x21: "Free Action",
    0xFF: "None",
}

TARGET_NAMES = {
    0: "Self",
    1: "Touch",
    2: "Projectile",
    3: "Area",
    4: "Target",
}

ELEMENT_NAMES = {
    0: "None",
    1: "Fire",
    2: "Frost",
    3: "Shock",
    4: "Magic",
}

ATTRIBUTE_NAMES = {
    0: "Strength",
    1: "Intelligence",
    2: "Willpower",
    3: "Agility",
    4: "Speed",
    5: "Endurance",
    6: "Personality",
    7: "Luck",
    0xFF: "None",
}


def parse_record(data: bytes, offset: int) -> dict:
    rec = data[offset: offset + RECORD_SIZE]

    # params: 6 × [p0, p1, p2] uint16_le
    params = []
    for i in range(6):
        base = i * 6
        p0, p1, p2 = struct.unpack_from("<HHH", rec, base)
        params.append([p0, p1, p2])

    target_type = rec[36]
    unknown = rec[37]
    element = rec[38]
    flags = struct.unpack_from("<H", rec, 39)[0]

    effects_raw = [rec[41], rec[42], rec[43]]
    sub_effects_raw = [rec[44], rec[45], rec[46]]
    attr_raw = [rec[47], rec[48], rec[49]]

    cost = struct.unpack_from("<H", rec, 50)[0]

    name_bytes = rec[52:85]
    name = name_bytes.split(b"\x00")[0].decode("latin-1")

    effects = [EFFECT_NAMES.get(e, f"0x{e:02x}") for e in effects_raw if e != 0xFF]
    attributes = [ATTRIBUTE_NAMES.get(a, f"0x{a:02x}") for a in attr_raw if a != 0xFF]

    return {
        "name": name,
        "cost": cost,
        "target": TARGET_NAMES.get(target_type, str(target_type)),
        "element": ELEMENT_NAMES.get(element, str(element)),
        "effects": effects,
        "effects_raw": [f"0x{e:02x}" for e in effects_raw],
        "sub_effects_raw": [f"0x{e:02x}" for e in sub_effects_raw],
        "affected_attributes": attributes,
        "flags": f"0x{flags:04x}",
        "params": params,
    }


def parse_spells():
    path = os.path.join(ARENA_DIR, "SPELLS.LST")
    with open(path, "rb") as f:
        data = f.read()

    spells = []
    for i in range(SPELLSG_COUNT):
        spell = parse_record(data, i * RECORD_SIZE)
        spell["id"] = i
        spells.append(spell)

    out_path = os.path.join(OUTPUT_DIR, "spells.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spells, f, indent=2, ensure_ascii=False)
    print(f"  wrote {len(spells)} spells -> {out_path}")
    return spells


if __name__ == "__main__":
    print("=== Parsing SPELLS.LST ===\n")
    spells = parse_spells()

    print("\n--- First 20 spells ---")
    for s in spells[:20]:
        fx = ", ".join(s["effects"]) or "—"
        print(f"  [{s['id']:3d}] {s['name']:<20} cost={s['cost']:4d}  "
              f"target={s['target']:<10} elem={s['element']:<6} effects=[{fx}]")

    print(f"\nTotal: {len(spells)} spells parsed.")
