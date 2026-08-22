---
name: arena_checks
description: "Resolves D20 attribute checks, skill tests, Sorcerer spell absorption, and custom spellmaking."
summary: "Prompt player checks with [arena_request_skill_check], roll NPC checks with [arena_roll_check], and resolve spells."
retrieval: always
---

# ATTRIBUTE & SKILL CHECK PROTOCOLS

## 1. Player Skill Checks
- Prompt player D20 tests for uncertain or risky actions:
  `[arena_request_skill_check(skill_name="...", attribute_name="...", dc=..., reason="...")]`
- **Suspense & Timing**: Describe the setup and initiation of the attempt. Conclude your turn immediately at the moment of action.
- **Resolution**: Do not narrate the outcome in the prompt message. Resolve success or failure in the following response once the player rolls.
- When casting spells during checks, deduct Magicka in the same turn: `[arena_spend_magicka(amount=...)]`.
- **Difficulty Classes**:
  - Easy: DC 10
  - Standard: DC 15
  - Challenging: DC 20
  - Legendary: DC 25

## 2. NPC & Monster Checks
- Resolve NPC actions, creature attacks, and saving throws immediately:
  `[arena_roll_check(attribute_name="...", attribute_value=..., dc=...)]`
  `[arena_roll_skill(skill_name="...", attribute_name="...", attribute_value=..., dc=...)]`

## 3. Spell Absorption & Custom Spells
- Negate incoming spells for Sorcerers: `[arena_sorcerer_absorb(intelligence=..., willpower=..., incoming_spell_tier=...)]`
- Create and memorize custom spells: `[arena_create_spell(...)]` -> `[arena_learn_spell(...)]`

## 4. Narrative Integration
- Translate roll results into immediate physical consequences.
- **Success**: Clean execution and tactical advantage.
- **Failure**: Complications, resistance, and rising danger.
