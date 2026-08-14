# ⚔️ LM-ARENA: THE ELDER SCROLLS TEXT ADVENTURE

An interactive, LLM-driven roleplaying text adventure recreating **The Elder Scrolls: Chapter I — Arena** (3E 389, The Imperial Simulacrum).

Embark on an epic journey across Tamriel to reconstruct the shattered **Staff of Chaos**, rescue Emperor Uriel Septim VII, and defeat the usurper Battlemage Jagar Tharn.

---

## 🌟 CORE FEATURES

### 🎲 D20 Narrative Mechanics
* **Transparent Roll System**: Character attributes (0–100 scale, centered at 50) determine standard d20 ability modifiers: `(Attribute - 50) / 10`.
* **Collapsible Action Log**: Combat attacks, stealth checks, lockpicking attempts, and spellcasting rolls are handled via background tool executions. Numerical mechanics remain neatly tucked inside collapsible tool dropdowns, keeping chat narrative fluid and immersive.
* **Dynamic Vitals**: Track **Health (HP)**, **Magicka (MP)**, and **Stamina** with real-time exhaustion penalties for reckless exertion.

### 🗺️ Vast World of Tamriel
* **Nine Provinces**: Explore Cyrodiil, Skyrim, Morrowind, High Rock, Hammerfell, Summerset Isle, Valenwood, Elsweyr, and Black Marsh.
* **Main Quest Dungeons**: Infiltrate all 8 legendary fragment locations: Fang Lair, Labyrinthian, Elden Grove, Halls of Colossus, Crystal Tower, Crypt of Hearts, Murkwood, and Dagoth Ur, before storming the Imperial Palace.
* **Tamrielic Calendar**: Realistic day, month, and season progression across all twelve Tamrielic months.

### 🛡️ Character & Inventory System
* **Playable Races & Classes**: Full support for all 8 original races and 18 classic Arena classes (Warrior, Mage, Thief archetypes).
* **Backpack & Grimoire**: Equip and manage weapons, armor, shields, torches, and enchanted jewelry, or drop items from your pack.
* **Arena Spellmaker**: Design custom spells with dynamic school and tier calculations (Destruction, Restoration, Alteration, Illusion, Mysticism, Conjuration, Thaumaturgy, Sorcery).
* **Passive Traits**: Race traits (Nord Cold Resistance, Breton Magic Resistance, Dark Elf Fire Resistance) and class abilities (Sorcerer passive Spell Absorption).

### 👥 Companions & Guides
* **Ria Silmane**: The spectral former apprentice to Jagar Tharn, communicating through mystical dream visions to guide your quest.
* **Procedural Companions**: Meet, hire, and adventure with local sellswords, spellcasters, and rogues encountered across Tamriel's taverns and cities.

### 📚 Comprehensive Lorebook Engine
* **Bestiary**: Complete statistics and lore grounding for 22 iconic Arena monsters, beasts, and Daedric entities.
* **Artifacts**: 16 legendary Tamrielic relics including Chrysamere, the Staff of Magnus, Auriel's Bow & Shield, and the Oghma Infinium.
* **World Info**: Factions, Nine Divines, Daedric Princes, city services, taverns, temples, and blacksmiths.

---

## 🛠️ INTERFACE CONTROLS

* **Vitality Pulse (Top-Left)**: Click the heart vitality bar to inspect your Character Status sheet, Vitals, Attributes, and Active Effects.
* **Backpack (Pouch Icon)**: Inspect inventory items, equip gear, view your grimoire, and manage gold.
* **Quest Log (Bookmark Icon)**: Review active main quest objectives and current campaign stages.
* **Player & Saves (User Icon)**: Switch characters, adjust identity, or manage distinct save game slots.
* **Follower Journals (Layers Icon)**: Access companion journals, memories, and shared knowledge.
* **Settings (Gear Icon)**: Configure local LLM connections, cloud models, and ComfyUI image generation.

---

## 🚀 GETTING STARTED

### Windows (Quick Start):
Double-click `run_local.bat` (or run `./run_local.ps1` in PowerShell).
Open your browser at **`http://localhost:5000`**

### Manual Installation:
1. Open a terminal in the project directory:
   ```bash
   python -m venv .venv
   ```
2. Activate the virtual environment:
   * **Windows**: `.venv\Scripts\activate`
   * **Mac/Linux**: `source .venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the application:
   ```bash
   python app.py
   ```
5. Navigate to **`http://localhost:5000`** in your browser.

---

## 📂 PROJECT STRUCTURE

* **`app.py`**: Main Flask backend server and REST API endpoints.
* **`engine/`**: Core game logic:
  * `mechanics.py`: d20 dice checks, combat resolution, and ability modifiers.
  * `character.py`: Character sheet definitions, inventory operations, and starting equipment.
  * `world_engine.py`: Travel calculations, calendar time progression, and world states.
  * `quest_tracker.py`: Main quest condition validation and stage advancements.
  * `spellmaker.py`: Arcane school classification and DC evaluation.
  * `save_manager.py`: Multi-slot save management and synchronization.
* **`core/lorebooks/`**: Context-triggered world information and lore injection:
  * `quest/`: The Imperial Simulacrum and Staff of Chaos storyline.
  * `character/`: Playable races and class archetypes.
  * `world/`: Bestiary, 16 Artifacts, Factions, Services, and Calendar.
  * `gameplay/`: Combat mechanics, magic schools, and d20 rules.
* **`core/world/`**: Static province, city, dungeon, and quest stage JSON definitions.
* **`core/programs/`**: Companion guide profiles, portraits, and dialog scripts (Ria Silmane).
* **`tools.py`**: LLM tool calls for dice rolling, travel, quest tracking, and spell evaluation.
* **`static/` & `templates/`**: Responsive web UI, CSS styling, and client-side application logic.
