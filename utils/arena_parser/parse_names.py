"""
parse_names.py — Phase 1A binary parser for NAMECHNK.DAT

Correct format (confirmed by tracing):
  Each race/gender chunk:
    uint16_le  total_syllables   (sum across all groups in this chunk)
    Then groups:
      uint8     group_syllable_count
      group_syllable_count x null-terminated strings
    ...repeat groups until total_syllables consumed

  Chunks repeat for each race × gender combination.

Group 0 = first-syllable prefixes (capitalize)
Group 1 = second-syllable suffixes (append directly)

Races in order (from OpenTESArena CharacterRaceLibrary):
  0=Human, 1=Elf, 2=DarkElf, 3=Argonian, 4=Khajiit,
  5=Redguard, 6=Nord, 7=Breton
Genders: Male, Female
"""

import json
import os

ARENA_DIR = r"c:\Users\Davy\Documents\My Games\Arena"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

RACES = ["Human", "Elf", "DarkElf", "Argonian", "Khajiit", "Redguard", "Nord", "Breton"]
GENDERS = ["Male", "Female"]


def read_chunk(data: bytes, pos: int):
    """Read one name chunk. Returns (groups, new_pos)."""
    if pos + 2 > len(data):
        return None, pos

    total = data[pos] | (data[pos + 1] << 8)
    pos += 2

    if total == 0 or total > 2000:
        return None, pos

    consumed = 0
    groups = []
    while consumed < total and pos < len(data):
        group_count = data[pos]
        pos += 1
        syllables = []
        for _ in range(group_count):
            try:
                end = data.index(0x00, pos)
            except ValueError:
                break
            syl = data[pos:end].decode("latin-1")
            syllables.append(syl)
            pos = end + 1
        groups.append(syllables)
        consumed += group_count

    return groups, pos


def parse_namechunks():
    path = os.path.join(ARENA_DIR, "NAMECHNK.DAT")
    with open(path, "rb") as f:
        data = f.read()

    chunks = []
    pos = 0
    chunk_id = 0

    while pos < len(data) - 2:
        groups, new_pos = read_chunk(data, pos)
        if groups is None:
            break

        # Build label: race × gender, cycling through
        race_idx = (chunk_id // 2) % len(RACES)
        gender = GENDERS[chunk_id % 2]
        label = f"{RACES[race_idx]}_{gender}"

        chunks.append({
            "id": chunk_id,
            "label": label,
            "prefixes": [s for s in groups[0] if s] if len(groups) > 0 else [],
            "suffixes": [s for s in groups[1] if s] if len(groups) > 1 else [],
            "groups": groups,
            "total_syllables": sum(len(g) for g in groups),
        })

        pos = new_pos
        chunk_id += 1

    out_path = os.path.join(OUTPUT_DIR, "name_chunks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"  wrote {len(chunks)} chunks -> {out_path}")
    return chunks


if __name__ == "__main__":
    print("=== Parsing NAMECHNK.DAT ===\n")
    chunks = parse_namechunks()

    print("\n--- Chunk summary ---")
    for c in chunks:
        pre = c["prefixes"][:4]
        suf = c["suffixes"][:4]
        print(f"  [{c['id']:2d}] {c['label']:<20}  {c['total_syllables']:3d} syls  "
              f"prefixes={pre}  suffixes={suf}")

    import random
    print("\n--- 8 example names (prefix+suffix) ---")
    for c in chunks[:4]:
        if c["prefixes"] and c["suffixes"]:
            for _ in range(2):
                name = random.choice(c["prefixes"]) + random.choice(c["suffixes"]).lower()
                print(f"  [{c['label']}] {name}")
