# LM-ARENA: THE ELDER SCROLLS TEXT ADVENTURE

An interactive, LLM-driven roleplaying text adventure recreating **The Elder Scrolls: Chapter I — Arena** (3E 389, The Imperial Simulacrum).

Embark across Tamriel to reconstruct the shattered **Staff of Chaos**, rescue Emperor Uriel Septim VII, and defeat the usurper Battlemage Jagar Tharn.

---

<p align="center">
  <img src="static/img/samplechat.png" alt="LM-Arena Gameplay Preview" width="700">
</p>

---

## FEATURES

### D20 Roleplay & Combat
* **Attribute Checks**: Classic attributes (Strength, Intelligence, Willpower, Agility, Speed, Endurance, Personality, Luck) determine modifiers for all trials.
* **Vitals & Exertion**: Track Health, Magicka, and Stamina in real time. Reckless maneuvers draw upon your physical reserves.
* **Fluid Prose**: Numerical dice rolls, checks, and inventory logs stay inside collapsible tool cards, keeping narrative prose immersive.

### The Realm of Tamriel
* **Nine Provinces**: Journey through Cyrodiil, Skyrim, Morrowind, High Rock, Hammerfell, Summerset Isle, Valenwood, Elsweyr, and Black Marsh.
* **The Main Quest**: Delve into all eight legendary dungeons—from Fang Lair to the Crypt of Hearts—before storming the Imperial Palace.
* **Tamrielic Calendar**: Authentic dates, hours, and seasonal progression across the Empire.

### Character & Arsenal
* **Classic Heritages & Classes**: All original heritages and 18 classic classes across Warrior, Mage, and Thief disciplines.
* **Backpack & Spells**: Manage weapons, armor, enchanted trinkets, and custom spells crafted in the Mages Guild.
* **Companions**: Guided by the spectral visions of Ria Silmane and sellswords met across Tamriel's taverns.

---

## GETTING STARTED

### Quick Start
Double-click `run_local.bat` (or `./run_local.ps1` in PowerShell, `./run_local.sh` on Linux/macOS).

### Recommended Setup
LM-Arena is tuned and tested against one reference configuration. Other models may work, but prompts, formatting rules, and tool calling are validated only against this one.

| Component | Reference |
|---|---|
| Chat LLM | **Equinox 31B** (Gemma 4 based, uncensored finetune), `Equinox-31B.i1-Q4_K_M.gguf` (~17.4 GB) |
| Context | 16384 tokens (`LOCAL_CONTEXT=16384`); a full prompt is already ~6.5k tokens, so 8192 leaves too little room as the story grows |
| KV cache | `q8_0` K/V with Flash Attention enabled, all layers on GPU (`LOCAL_GPU_LAYERS=99`) |
| Art | SDXL / Illustrious checkpoint via ComfyUI (`--lowvram`) |

**Why an uncensored finetune?** Mainstream instruct models tend to refuse or soften violence and dark themes that Elder Scrolls stories need.

### PC Requirements
Verified on: Ryzen 9 5900X, 32 GB RAM, AMD Radeon RX 7900 XTX (24 GB VRAM), Windows 64-bit.

| | Minimum (reference setup) | Notes |
|---|---|---|
| GPU | 24 GB VRAM | The 31B Q4 model uses ~18 GB; the rest goes to the KV cache and image generation |
| RAM | 32 GB | Model loading and ComfyUI |
| Storage | ~40 GB free | LLM ~17 GB, checkpoints and LoRAs ~13 GB, plus dependencies |
| OS | Windows 10/11 64-bit | Linux/macOS launch scripts are included but untested |

**Smaller GPUs:** with less than 24 GB, use a smaller GGUF (for example a ~12-14B model at Q4), lower `LOCAL_CONTEXT`, and reduce `LOCAL_GPU_LAYERS`. These configurations are untested, so expect to tune prompts and settings yourself. Image generation shares VRAM with the LLM; if it fails, keep `COMFYUI_ARGS=--lowvram`.

### Models
Place model files in the `models/` directory:
* **Chat LLM (GGUF)**: `models/llm/` (the recommended model above)
* **Art Checkpoints (SDXL / SD 1.5)**: `models/checkpoints/`
* **LoRAs**: `models/loras/`

### Manual Setup
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate # Linux/macOS
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch:
   ```bash
   python desktop.py
   # Or browser mode: python app.py -> http://localhost:5000
   ```

---

## LICENSE & DISCLAIMER

* **License**: LM-Arena's software engine and code are released under the [GNU Affero General Public License v3.0](LICENSE).
* **Trademark & Fan Content**: *The Elder Scrolls*, *Arena*, and all associated names, places, and lore are registered trademarks or copyright of ZeniMax Media Inc. / Bethesda Softworks LLC. This is an unofficial, non-commercial fan tribute and is not affiliated with or endorsed by Bethesda Softworks or ZeniMax Media.

