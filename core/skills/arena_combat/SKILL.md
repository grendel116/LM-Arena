---
name: arena_combat
description: "Resolves combat encounters: attack rolls, damage, healing, stamina, resting, and resource expenditure in The Elder Scrolls: Arena."
summary: "Resolve melee/ranged attacks with [arena_roll_combat], take damage with [arena_take_damage], heal with [arena_heal], spend/restore stamina with [arena_spend_stamina]/[arena_restore_stamina], and rest with [arena_rest]."
retrieval: vector
triggers: attack, combat, fight, strike, slash, weapon, damage, defend, parry, cast, spell, hp, stamina, magicka, rest, sleep, ambush, wound
---

# COMBAT, BESTIARY & RESOURCE RESOLUTION PROTOCOLS

When hostilities, ambushes, or physical confrontations occur between the player and creatures/NPCs:

## 1. Attack Resolution & Stamina Checks
- For attacks made by either the player or an adversary:
  `[arena_roll_combat(attacker_name="...", attacker_strength=..., attacker_agility=..., attacker_class_archetype="...", weapon_name="...", weapon_damage_tier=..., weapon_attribute="...", target_name="...", target_agility=...)]`
- **Stamina Impact on Combat**:
  - When the attacker's Stamina drops below 25% (or 0), they suffer **Low Stamina / Exhaustion** (-3 penalty / disadvantage to hit).
  - Heavy power strikes, dodging, and prolonged sprinting spend Stamina: `[arena_spend_stamina(amount=...)]`.
  - Catching breath or drinking stamina potions restores Stamina: `[arena_restore_stamina(amount=...)]`.

## 2. Damage & Healing Application
- When an attack connects against the player:
  `[arena_take_damage(amount=...)]`
- When healed via potion or Restoration spell:
  `[arena_heal(amount=...)]`
- When casting spells, spend Magicka (MP):
  `[arena_spend_magicka(amount=...)]`

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

## 5. Narrative Style
- Output the tool calls alongside your narrative text in a single turn.
- Interpret the outcomes into visceral sensory detail without reciting numbers.
- Threaten {{user}} with difficult encounters.

## 6. Death & Game Over Protocol
- When {{user}}'s health reaches 0 (hp_current <= 0 / dead: true), you MUST narrate their tragic death in visceral detail and declare a GAME OVER state.
- Output a detailed narrative of the hero collapsing and perishing in Tamriel. Do not allow the hero to survive or take further actions.