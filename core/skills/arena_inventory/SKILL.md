---
name: arena_inventory
description: "Manages player inventory, finding/looting items, equipment slots, shop trading, currency/gold, and item consumption."
summary: "Add looted/found items with [arena_add_item], remove used/sold items with [arena_remove_item], award gold with [arena_add_gold], and spend coins with [arena_spend_gold]."
retrieval: vector
---

# INVENTORY & ECONOMY PROTOCOLS

When the player acquires items, discovers loot, shops with merchants, or expends carried gear:

## 1. Item Acquisition & Looting
- When the player picks up, loots from a corpse, finds in a chest, or receives an item (such as keys, weapons, robes, potions, torches, scrolls, quest tokens):
  `[arena_add_item(item_name="...", item_type="...", quantity=1)]`
- Valid item types:
  - `"weapon"` (1-Handed blades, daggers, maces, bows)
  - `"2h_weapon"` (Claymores, battle axes, staves, halberds)
  - `"shield"` (Bucklers, round shields, tower shields)
  - `"torch"` / `"light"` (Light sources for dark dungeons)
  - `"armor"` / `"robes"` (Body attire)
  - `"helmet"` / `"hood"` / `"circlet"` (Head slot)
  - `"gauntlets"` / `"gloves"` (Hand slot)
  - `"boots"` / `"shoes"` (Foot slot)
  - `"amulet"` / `"necklace"` (Neck slot)
  - `"ring"` (Finger slot, limit 2)
  - `"potion"` (Health, spell point, cure disease)
  - `"scroll"` (Arcane spells)
  - `"tool"` / `"misc"` (Lockpicks, keys, ropes, maps, gems)

## 2. Consuming, Selling, or Dropping Items
- When the player drinks a potion, lights and expends a torch, loses a lockpick, hands over a key, or sells goods:
  `[arena_remove_item(item_name="...", quantity=1)]`

## 3. Gold & Financial Transactions
- When the player loots coins, receives quest rewards, or discovers hidden caches:
  `[arena_add_gold(amount=...)]`
- When the player purchases equipment, pays tavern lodging, bribes city guards, or pays temple tithes:
  `[arena_spend_gold(amount=...)]`

## 4. Narrative Integration
- Output the tool call in the same turn that the action occurs.
- Ground the description in sensory detail (e.g. the cold feel of forged iron, the weight of gold drakes jingling in a pouch, the smell of sulfur on a potion).
