---
name: arena_combat
description: "Resolves combat encounters: attack rolls, damage, healing, stamina, resting, and resource expenditure in The Elder Scrolls: Arena."
summary: "Creature attacks: [arena_roll_combat(attacker_name=\"...\", attack_name=\"...\")]. {{user}}'s successful spell/attack: [arena_damage_target(target_name=\"...\", source=\"...\")]. Hazards: [arena_take_damage]; healing: [arena_heal]; stamina: [arena_spend_stamina]/[arena_restore_stamina]; rest: [arena_rest]."
retrieval: always
triggers: attack, combat, fight, strike, slash, weapon, damage, defend, parry, cast, spell, hp, stamina, magicka, rest, sleep, ambush, wound, sparks, shock, blast, magic, enemy, enemies, skeleton, monster, creature, undead
---

# COMBAT & RESOURCES

Sequence each round: Request (DM) -> Check ({{user}}) -> Resolve & Retaliate (DM).

## Tool-Backed Outcomes (Mandatory)
Never narrate damage, healing, or death without its tool call in the same turn. Tool results are authoritative: narrate exactly what they report (miss = no wound, `defeated` = dead, otherwise still standing).
- Creature/NPC attacks on {{user}}: `[arena_roll_combat(attacker_name="...", attack_name="Bite/Claws/Sword/Spell")]` every round. Hostiles stay aggressive; never let them idle. It rolls to-hit, applies damage and status effects on a hit, and reports `dead`.
- {{user}}'s attacks and spells: narrate up to the moment of uncertainty, call `[arena_request_skill_check(...)]`, and stop. Never use `arena_roll_combat` with {{user}} as attacker.
- After a successful check: `[arena_damage_target(target_name="...", source="Spark")]`. It tracks the target's HP and reports `defeated`, `xp_reward`, and `loot`. On a failed check, the attack does nothing.
- Environmental harm (falls, drowning, traps, poison ticks): `[arena_take_damage(amount=N)]`, N scaled to severity (1-3 minor, 4-8 serious, 9+ severe). Healing (potion, Restoration): `[arena_heal(amount=N)]`.

## Resources
After the check resolves, spend Magicka `[arena_spend_magicka(amount=...)]` for spells and Stamina `[arena_spend_stamina(amount=...)]` for heavy maneuvers. Restore Stamina with `[arena_restore_stamina(amount=...)]`. Stamina below 25% gives -3 to hit.

## Rest
- Safe rest (6-8 h): `[arena_rest(hours=8, safe=True)]` restores HP, MP, and Stamina fully (Sorcerers regain MP only by Spell Absorption).
- Short breather (1-2 h): `[arena_rest(hours=2, safe=False)]` restores Stamina fully and ~35% HP and MP.
- Potions restore their pool instantly. City temples cure disease and poison and restore all vitals for a donation.

## World Rules
- Ghosts, Wraiths, Vampires, and Liches ignore mundane iron/steel; they need Silver, Elven, Dwarven, Mithril, Ebony, or spells.
- Creatures must fit the province's biome, culture, and history; no foreign species without a narrative reason.

## Death
{{user}} lives while hp_current > 0. At 0 (`dead: true`), narrate the fatal blow and declare GAME OVER.
