---
name: arena_checks
description: "Resolves D20 attribute checks, specialized skill tests (lockpicking, stealth, persuasion, climbing), Sorcerer spell absorption, and custom spellmaking."
summary: "Roll raw attribute tests with [arena_roll_check], specialized skill checks with [arena_roll_skill], Sorcerer spell absorption with [arena_sorcerer_absorb], and design spells with [arena_create_spell]."
retrieval: vector
triggers: roll, check, d20, lock, pick, lockpick, picklock, door, chest, stealth, sneak, hide, persuade, bribe, climb, jump, swim, strength, agility, endurance, intelligence, willpower, personality, speed, luck, absorb, spellmaker, create spell, craft spell
---

# ATTRIBUTE & SKILL CHECK PROTOCOLS

When the player attempts risky physical maneuvers, rogue actions, social influence, or magic crafting:

## 1. Skill Tests (Lockpicking, Stealth, Athletics)
- When picking a lock, sneaking past guards, jumping a chasm, or haggling:
  `[arena_roll_skill(skill_name="...", attribute_name="...", attribute_value=..., dc=...)]`
- Standard Difficulty Classes (DC):
  - Easy: DC 10
  - Standard: DC 15
  - Challenging: DC 20
  - Legendary: DC 25

## 2. Raw Attribute Checks
- For brute force strength tests, agility reflexes, endurance against poison, willpower resisting mind spells, or sheer luck:
  `[arena_roll_check(attribute_name="...", attribute_value=..., dc=...)]`

## 3. Sorcerer Spell Absorption
- When an enemy spell is cast at a Sorcerer class player:
  `[arena_sorcerer_absorb(intelligence=..., willpower=..., incoming_spell_tier=...)]`
- If successful, the incoming spell is negated and converted into player Spell Points.

## 4. Custom Spellmaker
- When the player creates or designs a custom spell:
  `[arena_create_spell(spell_description="...", school="...", tier=..., caster_intelligence=...)]`
- Followed by learning the spell card:
  `[arena_learn_spell(character_name="{{user}}", spell_name="...", school="...", tier=..., sp_cost=...)]`
- Expending spell points during casting:
  `[arena_spend_spell_points(character_name="{{user}}", amount=...)]`

## 5. Narrative Style
- Interpret the roll result directly into descriptive action.
- On success: describe clean execution (e.g. the lock tumblers clicking open, the footsteps silent against stone).
- On failure: describe complications or tension (e.g. the lockpick bending with a sharp snap, the scrape of gravel alerting a sentry).
