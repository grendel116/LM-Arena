"""
audit.py — Phase 2: Diff parsed Arena data against LM-Arena lorebooks + engine scripts.

Produces a structured gap report: what's missing, wrong, or unverifiable.
"""

import json
import os
import re
import sys

_here = os.path.dirname(os.path.abspath(__file__))   # utils/arena_parser/
ROOT    = os.path.dirname(os.path.dirname(_here))      # LM-Arena/
PARSED  = os.path.join(_here, "output")
LOREBOOKS = os.path.join(ROOT, "core", "lorebooks")
ENGINE = os.path.join(ROOT, "engine")

PASS  = "  ✓"
FAIL  = "  ✗"
WARN  = "  ?"
SEP   = "-" * 72

issues = []
passes = []

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def read_py(filename):
    path = os.path.join(ENGINE, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()

def ok(msg):
    passes.append(msg)
    print(f"{PASS}  {msg}")

def fail(msg, detail=""):
    issues.append({"msg": msg, "detail": detail})
    print(f"{FAIL}  {msg}")
    if detail:
        print(f"       {detail}")

def warn(msg, detail=""):
    issues.append({"msg": f"[WARN] {msg}", "detail": detail})
    print(f"{WARN}  {msg}")
    if detail:
        print(f"       {detail}")

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


# =============================================================================
# 1. CLASSES
# =============================================================================

section("AUDIT 1: classes.json vs class_mechanics.json (18 classes)")

truth_classes = load(os.path.join(PARSED, "class_mechanics.json"))
truth_names   = {c["name"] for c in truth_classes}
truth_by_name = {c["name"]: c for c in truth_classes}

current_classes = load(os.path.join(LOREBOOKS, "character", "classes.json"))

# Figure out the top-level key
if isinstance(current_classes, list):
    cur_list = current_classes
elif "entries" in current_classes:
    cur_list = current_classes["entries"]
elif "classes" in current_classes:
    cur_list = current_classes["classes"]
else:
    cur_list = [v for v in current_classes.values() if isinstance(v, dict)]

cur_names = {c.get("name", c.get("class_name", "")) for c in cur_list}
print(f"\n  Current file has {len(cur_list)} entries. Source truth has {len(truth_classes)}.\n")

# Count
if len(cur_list) == 18:
    ok("Class count = 18")
else:
    fail(f"Class count = {len(cur_list)}, should be 18",
         f"Missing: {truth_names - cur_names}")

# Check each class
for tc in truth_classes:
    name = tc["name"]
    match = next((c for c in cur_list
                  if c.get("name","").lower() == name.lower()
                  or c.get("class_name","").lower() == name.lower()), None)
    if not match:
        fail(f"Class '{name}' missing from lorebook")
        continue

    # HP die
    if "hp_die" not in match and "health_die" not in match and "hit_die" not in match:
        fail(f"'{name}' missing hp_die (should be d{tc['hp_die']})")
    else:
        ok(f"'{name}' has hp_die field")

    # SP multiplier
    sp_key = next((k for k in ("sp_multiplier","spell_points_multiplier","mp_multiplier") if k in match), None)
    if sp_key is None:
        fail(f"'{name}' missing sp_multiplier (should be {tc['sp_multiplier']})")

    # Category
    if "category" not in match:
        warn(f"'{name}' missing 'category' (mage/thief/warrior)")

    # Thieving divisor
    if "thieving_divisor" not in match:
        warn(f"'{name}' missing thieving_divisor (should be {tc['thieving_divisor']})")


# =============================================================================
# 2. BESTIARY
# =============================================================================

section("AUDIT 2: bestiary.json structure + schema key")

bestiary = load(os.path.join(LOREBOOKS, "world", "bestiary.json"))

# Schema key check
if "entries" in bestiary:
    monsters = bestiary["entries"]
    ok("Top-level key is 'entries'")
elif "monsters" in bestiary:
    monsters = bestiary["monsters"]
    fail("Top-level key is 'monsters' — mechanics.py reads 'entries'",
         "Fix: rename key to 'entries' in bestiary.json OR update mechanics.py")
else:
    monsters = []
    fail("bestiary.json has no 'entries' or 'monsters' key")

print(f"\n  {len(monsters)} creatures in lorebook. Source truth: 24.\n")

if len(monsters) >= 24:
    ok(f"Creature count {len(monsters)} >= 24")
else:
    warn(f"Only {len(monsters)} creatures — may be missing some of the 24")

# Check fields on first creature
if monsters:
    first = monsters[0] if isinstance(monsters, list) else list(monsters.values())[0]
    required_fields = {
        "name": "string name",
        "hp": "HP range (min/max)",
        "damage": "damage range",
        "xp_base": "base XP reward",
        "disease_chance": "% chance to inflict disease",
        "is_undead": "undead flag (bool)",
        "loot_chance": "loot roll probability",
    }
    for field, desc in required_fields.items():
        if field in first:
            ok(f"Creature has field '{field}'")
        else:
            fail(f"Creature missing '{field}' — {desc}")


# =============================================================================
# 3. character.py — DEFAULT_SHEET
# =============================================================================

section("AUDIT 3: engine/character.py — DEFAULT_SHEET & derived stat formulas")

char_src = read_py("character.py")

# HP check
hp_match = re.search(r'"hp"\s*:\s*(\d+)', char_src)
if hp_match:
    hp_val = int(hp_match.group(1))
    if hp_val == 30:
        fail(f"DEFAULT_SHEET hp={hp_val} is hardcoded",
             "Should be 25 + 1d{class.hp_die}. Mage=26-31, Barbarian=26-37.")
    else:
        warn(f"DEFAULT_SHEET hp={hp_val} — verify against formula: 25 + 1d{{class.hp_die}}")
else:
    warn("Could not find 'hp' in DEFAULT_SHEET")

# MP check
mp_match = re.search(r'"(?:mp|spell_points|max_mp)"\s*:\s*(\d+)', char_src)
if mp_match:
    mp_val = int(mp_match.group(1))
    # Mage with INT=50 → 50 * 2.0 = 100. Warrior classes → 0.
    if mp_val > 0:
        warn(f"DEFAULT_SHEET mp={mp_val} hardcoded — should be INT × class.sp_multiplier "
             f"(0 for warrior/thief classes, INT×2.0 for Mage)")
else:
    warn("Could not find 'mp'/'spell_points' in DEFAULT_SHEET")

# Damage bonus formula
if "damage_bonus" in char_src or "calculateDamageBonus" in char_src:
    ok("damage_bonus function present")
else:
    fail("damage_bonus formula missing",
         "Formula: 0 if STR<=43, else (STR-48)//5")

# Bonus to hit
if "bonus_to_hit" in char_src or "bonusToHit" in char_src:
    ok("bonus_to_hit function present")
else:
    fail("bonus_to_hit formula missing",
         "Formula: -1 if AGI<=45, 0 if AGI==46, else (AGI-50)//5")

# Carry weight
if "max_weight" in char_src or "carry_weight" in char_src or "calculateMaxWeight" in char_src:
    ok("carry weight formula present")
else:
    fail("carry weight missing", "Formula: STR × 2 (in kg)")

# Stamina
if "stamina" in char_src.lower():
    ok("stamina modeled in character.py")
else:
    fail("stamina not modeled", "Formula: STR + END")


# =============================================================================
# 4. mechanics.py
# =============================================================================

section("AUDIT 4: engine/mechanics.py — combat & skill checks")

mech_src = read_py("mechanics.py")

# Bestiary access key
if '"entries"' in mech_src:
    ok('mechanics.py reads bestiary["entries"]')
elif '"monsters"' in mech_src:
    fail('mechanics.py reads bestiary["monsters"] — mismatches lorebook key')
else:
    warn("mechanics.py bestiary key not found")

# To-hit formula
if "isMeleeHitSuccessful" in mech_src or "chance1" in mech_src or "scale100to256" in mech_src:
    ok("To-hit formula implemented")
else:
    fail("Arena to-hit formula not implemented",
         "Formula: chance1=128+scale100to256((atkLvl-defLvl)*5)+luck+racial+hit-AC; "
         "chance2=scale100to256(atkLvl)+51; hit if rand(256)<max(c1,c2)")

# Damage bonus applied
if "damage_bonus" in mech_src or "str" in mech_src.lower():
    ok("Damage bonus referenced in mechanics")
else:
    warn("STR damage bonus not applied in mechanics.py")

# Disease chance
if "disease" in mech_src.lower():
    ok("Disease mechanic referenced")
else:
    fail("Disease chance not implemented",
         "Creatures have disease_chance %; on hit, roll; apply STR/AGI/SPD/END drain")

# Undead check
if "undead" in mech_src.lower() or "is_undead" in mech_src:
    ok("Undead flag checked")
else:
    fail("Undead flag not used",
         "Undead immune to disease/poison; affected by Silver/Mithril/Holy weapons")


# =============================================================================
# 5. RACES
# =============================================================================

section("AUDIT 5: races.json — 8 races, attributes, province linkage")

races = load(os.path.join(LOREBOOKS, "character", "races.json"))
race_list = (races if isinstance(races, list)
             else races.get("entries", races.get("races", [v for v in races.values() if isinstance(v, (dict, list))])))
if race_list and isinstance(race_list, list) and isinstance(race_list[0], str):
    race_list = []

print(f"\n  {len(race_list)} races in lorebook. Expected 8.\n")

if len(race_list) == 8:
    ok("Race count = 8")
else:
    fail(f"Race count = {len(race_list)}, should be 8")

for race in race_list:
    name = race.get("name","?")
    if "province_id" not in race and "province" not in race:
        warn(f"Race '{name}' missing province linkage")
    if "base_attributes" not in race and "attributes" not in race and "stat_modifiers" not in race:
        warn(f"Race '{name}' missing numeric base_attributes (from raceAttributes[8])")


# =============================================================================
# 6. WEAPONS — new file needed
# =============================================================================

section("AUDIT 6: items — weapons.json (new) vs lorebooks")

parsed_weapons = load(os.path.join(PARSED, "weapons.json"))

# Check if any weapons lorebook exists
weapon_lb_path = os.path.join(LOREBOOKS, "world", "weapons.json")
item_lb_path   = os.path.join(LOREBOOKS, "gameplay", "items.json")

if os.path.exists(weapon_lb_path):
    ok("core/lorebooks/world/weapons.json exists")
    cur_wpn = load(weapon_lb_path)
    cur_wpn_list = cur_wpn if isinstance(cur_wpn, list) else cur_wpn.get("weapons", [])
    if len(cur_wpn_list) >= 18:
        ok(f"{len(cur_wpn_list)} weapons in lorebook (expected 18)")
    else:
        fail(f"Only {len(cur_wpn_list)} weapons — need all 18 (IDs 0-17)")
else:
    fail("weapons.json lorebook MISSING",
         f"Create from parsed output: {len(parsed_weapons)} weapons ready")

if os.path.exists(item_lb_path):
    warn("gameplay/items.json exists — check if it duplicates weapon data")


# =============================================================================
# 7. CALENDAR lorebook — verify against Arena data
# =============================================================================

section("AUDIT 7: world/calendar.json — 12 months, 30 days, time brackets")

cal = load(os.path.join(LOREBOOKS, "world", "calendar.json"))

months = cal.get("months", [])
if len(months) == 12:
    ok("12 months defined")
else:
    fail(f"{len(months)} months defined — should be 12")

days_per = cal.get("days_per_month", None)
if days_per == 30:
    ok("days_per_month = 30")
elif days_per is not None:
    fail(f"days_per_month = {days_per} — should be 30")
else:
    warn("days_per_month field missing from calendar.json")

time_brackets = cal.get("time_of_day", cal.get("time_brackets", []))
if len(time_brackets) >= 6:
    ok(f"{len(time_brackets)} time-of-day brackets defined")
else:
    fail(f"Only {len(time_brackets)} time brackets — Arena has 6: Dawn/Morning/Afternoon/Dusk/Evening/Night",
         "Source: ArenaClockUtils.h")

holidays = cal.get("holidays", [])
if len(holidays) >= 15:
    ok(f"{len(holidays)} holidays defined")
else:
    warn(f"Only {len(holidays)} holidays — Arena has 15 named festivals")


# =============================================================================
# 8. DUNGEONS — new lorebook needed
# =============================================================================

section("AUDIT 8: quest/simulacrum.json vs dungeon names from DUNGEON.TXT")

parsed_dungeons = load(os.path.join(PARSED, "dungeons.json"))
parsed_names = {d["name"] for d in parsed_dungeons}

sim = load(os.path.join(LOREBOOKS, "quest", "simulacrum.json"))
sim_str = json.dumps(sim)

print(f"\n  Checking 8 dungeon names against simulacrum.json...\n")
for d in parsed_dungeons:
    name = d["name"]
    piece = d["staff_piece"]
    if name.lower() in sim_str.lower():
        ok(f"'{name}' ({piece} piece) found in simulacrum.json")
    else:
        fail(f"'{name}' ({piece} piece) NOT found in simulacrum.json")


# =============================================================================
# 9. SPELLS — spellmaker.py vs parsed data
# =============================================================================

section("AUDIT 9: engine/spellmaker.py vs 128 parsed spells")

spell_src = read_py("spellmaker.py")
parsed_spells = load(os.path.join(PARSED, "spells.json"))

# Check if spells are loaded from file
if "spells.json" in spell_src or "SPELLS" in spell_src:
    ok("spellmaker.py references spell data file")
else:
    fail("spellmaker.py does not load from spells.json",
         f"128 spells parsed and ready in output/spells.json")

# Check for effect templates
parsed_effects = load(os.path.join(PARSED, "spell_effects.json"))
if "spell_effects" in spell_src or "SPELLMKR" in spell_src or "effect_template" in spell_src:
    ok("spellmaker.py references effect templates")
else:
    fail("spellmaker.py missing 43 effect templates from SPELLMKR.TXT",
         "Load from output/spell_effects.json")

# Check for school restrictions
if "school" in spell_src.lower() or "mage_only" in spell_src or "allowed" in spell_src:
    ok("Spell school restrictions present in spellmaker")
else:
    warn("Spell school/class restrictions not enforced in spellmaker.py")


# =============================================================================
# SUMMARY
# =============================================================================

print(f"\n{'=' * 72}")
print(f"  AUDIT COMPLETE")
print(f"{'=' * 72}")
print(f"\n  PASSED : {len(passes)}")
print(f"  ISSUES : {len(issues)}")
print()

failures = [i for i in issues if not i["msg"].startswith("[WARN]")]
warnings = [i for i in issues if i["msg"].startswith("[WARN]")]

print(f"  FAILURES ({len(failures)}):")
for i, iss in enumerate(failures, 1):
    print(f"    {i:2d}. {iss['msg']}")
    if iss["detail"]:
        print(f"        -> {iss['detail'][:100]}")

print(f"\n  WARNINGS ({len(warnings)}):")
for i, iss in enumerate(warnings, 1):
    print(f"    {i:2d}. {iss['msg'].replace('[WARN] ','')}")

# Save machine-readable report
report = {
    "passed": len(passes),
    "failed": len(failures),
    "warned": len(warnings),
    "failures": failures,
    "warnings": warnings,
}
report_path = os.path.join(ROOT, "utils", "arena_parser", "output", "audit_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f"\n  Full report saved: {report_path}\n")
