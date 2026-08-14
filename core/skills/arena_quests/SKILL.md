---
name: arena_quests
description: "Tracks main quest chapter progression, Staff of Chaos fragments, province-to-province travel, and dungeon milestones in The Elder Scrolls: Arena."
summary: "Advance main quest stages with [arena_advance_stage], travel across Tamriel with [arena_travel], and retrieve location data with [arena_get_location]."
retrieval: vector
triggers: quest, escape, dungeon, imperial dungeon, shift gate, gate, riddle, travel, journey, province, cyrodiil, hammerfell, skyrim, morrowind, high rock, valenwood, elsweyr, summerset, black marsh, fang lair, labyrinthian, crystal tower, crypt of hearts, elden grove, halls of colossus, murkwood, dagoth ur, imperial palace, fragment, staff of chaos, ria silmane, jagar tharn, milestone, vision
---

# QUEST & WORLD TRAVEL PROTOCOLS

When the player completes narrative milestones, seeks Staff of Chaos fragments, or journeys across Tamriel:

## 1. Main Quest Advancement
- When the player fulfills the requirements of their active main quest stage (e.g. solving the Shift Gate riddle in the Imperial Dungeon, acquiring a Staff fragment, reaching a ruler, or entering the Imperial Palace):
  `[arena_advance_stage(character_name="{{user}}")]`
- This updates `world_state.json`, triggers spectral vision flags for Ria Silmane, and updates the player's active Quest Journal.

## 2. Fast Travel Across Provinces & Cities
- When the player journeys between provinces or travels to specific settlements:
  `[arena_travel(character_name="{{user}}", destination_province="...", destination_city="...")]`
- This advances the in-game Tamrielic calendar and updates local weather and climate state.

## 3. Location Grounding
- To query current regional geography, weather, and date context:
  `[arena_get_location(character_name="{{user}}")]`

## 4. Narrative Integration
- Never break immersion by saying "Quest stage advanced to 20".
- Describe the shift in the environment (e.g. the roar of the teleporting Shift Gate, the dusty horizon of Hammerfell, or Ria's sorrowful spirit appearing in a dream).
