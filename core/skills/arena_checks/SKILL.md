---
name: arena_checks
description: "Resolves D20 attribute checks, skill tests, Sorcerer spell absorption, and custom spellmaking."
summary: "Narrate the attempt and physical tension up to the moment of uncertainty, then prompt player checks with [arena_request_skill_check(skill_name=\"...\", attribute_name=\"...\", dc=..., reason=\"...\")]. Await the roll before resolving outcomes."
retrieval: always
triggers: check, roll, dc, attempt, climb, jump, lockpick, pick lock, lock, inspect, investigate, disarm, spell, cast, magic, attack, strike, shoot, sparks, shock, blast, heal, fight, swing, dodge, flee, run, sneak, hide
---

# ATTRIBUTE & SKILL CHECK PROTOCOLS

## 1. Player Checks & Resolution Sequence
- **Sequence**: Request (DM) -> Check (User) -> Spend & Narrate (DM).
- **Phase 1: Request (DM)**:
  - When {{user}} casts a spell, attacks, or attempts an action with an uncertain outcome:
    Narrate the physical action, sensory environment, and tension leading up to the crux of difficulty, then call:
    `[arena_request_skill_check(skill_name="...", attribute_name="...", dc=..., reason="...")]`
  - Await the roll. Never resolve the outcome or spend resources until {{user}} rolls.
- **Phase 2: Check (User)**:
  - {{user}} rolls the D20 via the game interface.
- **Phase 3: Spend & Narrate (DM)**:
  - In the subsequent response, deduct required resources:
    - Spells: `[arena_spend_magicka(amount=...)]`
    - Physical exertion: `[arena_spend_stamina(amount=...)]`
  - Narrate the physical consequences reflecting the roll outcome.
- **Difficulty Classes**:
  - Spellcasting: Minor (DC 8), Apprentice (DC 11), Journeyman (DC 14), Expert (DC 17), Master (DC 20)
  - Physical Tasks: Easy (DC 10), Standard (DC 15), Challenging (DC 20), Legendary (DC 25)

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
