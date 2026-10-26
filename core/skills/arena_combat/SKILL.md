---
name: arena_combat
description: "Resolves combat encounters: attack rolls, damage, healing, stamina, resting, and resource expenditure in The Elder Scrolls: Arena."
summary: "Resolve creature/adversary attacks with [arena_roll_combat(attacker_name=\"...\", weapon_name=\"...\")], environmental damage with [arena_take_damage], heal with [arena_heal], spend/restore stamina with [arena_spend_stamina]/[arena_restore_stamina], and rest with [arena_rest]."
retrieval: always
triggers: attack, combat, fight, strike, slash, weapon, damage, defend, parry, cast, spell, hp, stamina, magicka, rest, sleep, ambush, wound, sparks, shock, blast, magic, enemy, enemies, skeleton, monster, creature, undead
---

# COMBAT, BESTIARY & RESOURCE RESOLUTION PROTOCOLS

When hostilities, ambushes, or physical confrontations occur between the player and creatures/NPCs:

## 1. Attack & Combat Resolution
- **Adversary Attacks (Mandatory in Combat)**: In combat rounds, hostile creatures and NPCs do not remain passive. Resolve their attacks against {{user}} every round with:
  `[arena_roll_combat(attacker_name="[Monster/NPC Name]", weapon_name="[Attack/Weapon Type]")]`
  *(The tool automatically calculates to-hit vs Defense DC, rolls authentic damage, applies on-hit status effects, and deducts HP directly from {{user}}'s character sheet if it connects).*
- **Player Attacks & Spells**: When {{user}} attacks, casts a spell, or takes an offensive action:
  - Describe the strike, cast, or maneuver leading up to the impact, then prompt {{user}} with: `[arena_request_skill_check(skill_name="...", attribute_name="...", dc=..., reason="...")]`
  - Await {{user}}'s roll. Never roll `arena_roll_combat` with {{user}} as the attacker, and do not pre-spend resources or narrate the outcome until {{user}} rolls.
- **Stamina Impact on Combat**:
  - When the attacker's Stamina drops below 25% (or 0), they suffer **Low Stamina / Exhaustion** (-3 penalty / disadvantage to hit).
  - Heavy power strikes, dodging, and prolonged sprinting spend Stamina: `[arena_spend_stamina(amount=...)]` (applied during resolution).
  - Catching breath or drinking stamina potions restores Stamina: `[arena_restore_stamina(amount=...)]`.

## 2. Damage, Healing & Resource Expenditure
- Resource deduction occurs in the resolution turn after the player rolls:
  - When casting spells, spend Magicka (MP): `[arena_spend_magicka(amount=...)]`
  - When executing heavy physical maneuvers, spend Stamina: `[arena_spend_stamina(amount=...)]`
- For adversary attacks, `[arena_roll_combat]` automatically applies damage on hit. Use `[arena_take_damage(amount=...)]` only for environmental hazards, falling, traps, and lingering poison ticks.
- When healed via potion or Restoration spell: `[arena_heal(amount=...)]`

## 3. Resource Restoration & Resting
- **Resting at an Inn or Safe Camp** (6–8 hours):
  `[arena_rest(hours=8, safe=True)]`
  - Restores **Health (HP)**, **Magicka (MP)**, and **Stamina** to 100% (Note: *Sorcerers* do not regenerate MP through resting; they rely on Spell Absorption).
- **Short Breather / Unsafe Rest** (1–2 hours):
  `[arena_rest(hours=2, safe=False)]`
  - Restores **Stamina** to 100% and recovers ~35% of Health and Magicka.
- **Potions & Temple Blessings**:
  - Health Potions, Magicka Potions, and Stamina Potions instantly restore their respective pools.
  - City Temples cure diseases, poisons, and restore full vitals upon donation.

## 4. Material Immunities & Regional Ecology
- Ethereal undead (**Ghosts, Wraiths**), **Vampires**, and **Liches** are immune to mundane iron/steel weapons and require **Silver**, **Elven**, **Dwarven**, **Mithril**, **Ebony**, or **Spells**.
- **Regional Ecology**: Generate creatures whose natural habitat matches the current province's biome, culture, and historical inhabitants. Do not introduce creatures endemic to other provinces unless the narrative explicitly provides a reason for their presence.

## 5. Narrative Style & Turn Structure
- **Sequence**: Request (DM) -> Check (User) -> Resolve & Retaliate (DM).
- **Player Attack / Spell**: When {{user}} takes an offensive action, describe the tension and prompt `[arena_request_skill_check]`. Conclude your turn so {{user}} can roll.
- **Resolution & Adversary Turn**: In the response after {{user}} rolls (or when adversaries strike first), spend player resources (`[arena_spend_magicka]` / `[arena_spend_stamina]`), execute adversary attacks with `[arena_roll_combat(attacker_name="...", weapon_name="...")]`, and narrate the sensory consequences.
- In active combat, always keep adversaries dangerous and aggressive. Do not let monsters stand idle while the party fights.

## 6. Death & Game Over Protocol
- The hero remains alive while hp_current > 0.
- When {{user}}'s health reaches 0 (hp_current <= 0 / dead: true), narrate their fatal blow in visceral detail and declare a GAME OVER state. Do not allow survival once HP is 0.