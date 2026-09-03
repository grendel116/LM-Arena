---
name: arena_quests
description: "Tracks main quest chapter progression, Staff of Chaos fragments, province-to-province travel, and dungeon milestones in The Elder Scrolls: Arena."
summary: "Advance main quest stages with [arena_advance_stage], travel across Tamriel with [arena_travel], and retrieve location data with [arena_get_location]."
retrieval: vector
triggers: quest, stage, advance, staff of chaos, shift gate, portal, province, fast travel
---

# QUEST & WORLD TRAVEL PROTOCOLS

When the player completes narrative milestones, seeks Staff of Chaos fragments, or journeys across Tamriel:

## 1. Main Quest Advancement
- When the player fulfills the requirements of their active main quest stage (e.g. solving the Shift Gate riddle in the Imperial Dungeon, acquiring a Staff fragment, reaching a ruler, or entering the Imperial Palace):
  `[arena_advance_stage()]`
- To jump or set a specific chapter stage directly:
  `[arena_set_quest_stage(stage_number=...)]`
- This updates `world_state.json`, triggers spectral vision flags for Ria Silmane, and updates the player's active Quest Journal.

## 2. Setting Location & Portal Transit
- When the player steps through a Shift Gate, enters or exits a dungeon, or arrives in a specific town or wilderness:
  `[arena_set_location(province="...", location_name="...")]`

## 3. Fast Travel Across Provinces & Cities
- When the player journeys overland between provinces or travels to specific settlements:
  `[arena_travel(destination_province="...", destination_city="...")]`
- This advances the in-game Tamrielic calendar and updates local weather and climate state.

## 4. Location Grounding
- To query current regional geography, weather, and date context:
  `[arena_get_location()]`


## 5. Procedural Side Quests & Rumors
- **Creating a Side Quest**: When {{user}} takes on a commission or task:
  `[add_quest(title="...", notes="Objective 1\nObjective 2\nObjective 3", location="...")]`
- **Advancing a Side Quest**: When {{user}} completes an active objective for a side quest:
  `[arena_advance_side_quest(quest_id="...")]`
- **Completing / Archiving a Side Quest**:
  `[arena_complete_side_quest(quest_id="...")]`
