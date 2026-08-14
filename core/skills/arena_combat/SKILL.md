---
name: arena_combat
description: "Resolves combat encounters, enemy strikes, damage calculations, healing, stamina expenditure, rest recovery, bestiary HP tracking, and material immunities in The Elder Scrolls: Arena."
summary: "Resolve melee/ranged attacks with [arena_roll_combat], take damage with [arena_take_damage], heal with [arena_heal], spend/restore stamina with [arena_spend_stamina]/[arena_restore_stamina], and rest with [arena_rest]."
retrieval: vector
triggers: attack, fight, strike, enemy, blade, combat, damage, wound, ambush, monster, hit, rat, giant rat, goblin, skeleton, zombie, ghoul, spider, orc, minotaur, troll, ghost, wraith, atronach, flame atronach, frost atronach, storm atronach, winged twilight, medusa, vampire, lich, cliff racer, nix hound, draugr, dune ripper, senche raht, spriggan, harpy, werewolf, slash, dodge, parry, initiative, heal, rest, sleep, camp, inn, potion, poison, paralysis, disease, stamina, fatigue, exhaust, winded
---

# COMBAT, BESTIARY & RESOURCE RESOLUTION PROTOCOLS

When hostilities, ambushes, or physical confrontations occur between the player and creatures/NPCs:

## 1. Attack Resolution & Stamina Checks
- For attacks made by either the player or an adversary:
  `[arena_roll_combat(attacker_name="...", attacker_strength=..., attacker_agility=..., attacker_class_archetype="...", weapon_name="...", weapon_damage_tier=..., weapon_attribute="...", target_name="...", target_agility=...)]`
- **Stamina Impact on Combat**:
  - When the attacker's Stamina drops below 25% (or 0), they suffer **Low Stamina / Exhaustion** (-3 penalty / disadvantage to hit).
  - Heavy power strikes, dodging, and prolonged sprinting spend Stamina: `[arena_spend_stamina(character_name="{{user}}", amount=...)]`.
  - Catching breath or drinking stamina potions restores Stamina: `[arena_restore_stamina(character_name="{{user}}", amount=...)]`.

## 2. Damage & Healing Application
- When an attack connects against the player:
  `[arena_take_damage(character_name="{{user}}", amount=...)]`
- When healed via potion or Restoration spell:
  `[arena_heal(character_name="{{user}}", amount=...)]`
- When casting spells, spend Magicka (MP):
  `[arena_spend_magicka(character_name="{{user}}", amount=...)]`

## 3. Resource Restoration & Resting
- **Resting at an Inn or Safe Camp** (6–8 hours):
  `[arena_rest(character_name="{{user}}", hours=8, safe=True)]`
  - Restores **Health (HP)**, **Magicka (MP)**, and **Stamina** to 100% (Note: *Sorcerers* do not regenerate MP through resting; they rely on Spell Absorption).
- **Short Breather / Unsafe Rest** (1–2 hours):
  `[arena_rest(character_name="{{user}}", hours=2, safe=False)]`
  - Restores **Stamina** to 100% and recovers ~35% of Health and Magicka.
- **Potions & Temple Blessings**:
  - Health Potions, Magicka Potions, and Stamina Potions instantly restore their respective pools.
  - City Temples cure diseases, poisons, and restore full vitals upon donation.

## 4. Canonical TES Creature Retcons & Material Immunities
- Golems are **Atronachs** (`Flame Atronach`, `Frost Atronach`, `Storm Atronach`).
- Homunculus is **Winged Twilight**.
- Ethereal undead (**Ghosts, Wraiths**), **Vampires**, and **Liches** are immune to mundane iron/steel weapons and require **Silver**, **Elven**, **Dwarven**, **Mithril**, **Ebony**, or **Spells**.

## 5. Narrative Style
- Output the tool calls alongside your narrative text in a single turn.
- Interpret the outcomes directly into visceral sensory detail without reciting numbers.
