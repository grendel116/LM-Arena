import sys
import os
import json

# Ensure the parent directory is in sys.path so we can import variables package
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from variables.settings import VARIABLES_DIR

_settings_cache: dict | None = None
_settings_mtime: float = 0.0

def _get_settings_path() -> str:
    return os.path.normpath(os.path.join(VARIABLES_DIR, "project_settings.json"))

def _load_settings() -> dict:
    global _settings_cache, _settings_mtime
    path = _get_settings_path()
    if os.path.exists(path):
        try:
            mtime = os.path.getmtime(path)
            if _settings_cache is not None and mtime == _settings_mtime:
                return _settings_cache
            with open(path, "r", encoding="utf-8") as f:
                _settings_cache = json.load(f)
                _settings_mtime = mtime
                return _settings_cache
        except Exception as e:
            print(f"Error loading project settings: {e}")
    return {}

def _save_settings(settings: dict):
    global _settings_cache, _settings_mtime
    path = _get_settings_path()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, path)
        _settings_cache = settings
        _settings_mtime = os.path.getmtime(path)
    except Exception as e:
        print(f"Error saving project settings: {e}")


def get_active_follower() -> str:
    settings = _load_settings()
    active_fol = settings.get("active_follower") or os.getenv("ACTIVE_FOLLOWER") or "ria_silmane"

    target_folder = os.path.normpath(os.path.join(PARENT_DIR, 'core', 'followers', active_fol))
    if not os.path.isdir(target_folder) and active_fol != "ria_silmane":
        active_fol = "ria_silmane"
        target_folder = os.path.normpath(os.path.join(PARENT_DIR, 'core', 'followers', active_fol))

    os.environ["ACTIVE_FOLLOWER"] = active_fol

    current_folders = settings.get("folders", [])
    current_active = settings.get("active_follower")

    needs_update = False
    if current_active != active_fol:
        needs_update = True
    if not current_folders or os.path.normpath(current_folders[0]) != target_folder:
        needs_update = True

    if needs_update:
        settings["active_follower"] = active_fol
        settings["folders"] = [target_folder]
        _save_settings(settings)

    return active_fol

def set_active_follower(follower_id: str):
    os.environ["ACTIVE_FOLLOWER"] = follower_id
    settings = _load_settings()
    settings["active_follower"] = follower_id
    default_folder = os.path.normpath(os.path.join(PARENT_DIR, 'core', 'followers', follower_id))
    settings["folders"] = [default_folder]
    _save_settings(settings)

def get_active_user() -> str:
    settings = _load_settings()
    active_usr = settings.get("active_user") or os.getenv("ACTIVE_USER") or "eternal_champion"

    os.environ["ACTIVE_USER"] = active_usr

    if settings.get("active_user") != active_usr:
        settings["active_user"] = active_usr
        _save_settings(settings)

    return active_usr

def get_player_name() -> str:
    """Returns the active player's name from their character sheet."""
    try:
        from core.character import load_character
        return load_character().get("name") or "Eternal Champion"
    except Exception:
        return "Eternal Champion"

def set_active_user(username: str):
    os.environ["ACTIVE_USER"] = username
    settings = _load_settings()
    settings["active_user"] = username
    _save_settings(settings)

def get_tts_voice() -> str:
    settings = _load_settings()
    active_fol = settings.get("active_follower")
    if active_fol:
        follower_voices = settings.get("follower_voices", {})
        voice = follower_voices.get(active_fol)
        if voice:
            return voice
    voice = settings.get("tts_voice") or os.getenv("TTS_VOICE", "af_heart")
    return voice

def set_tts_voice(voice: str):
    os.environ["TTS_VOICE"] = voice
    settings = _load_settings()
    settings["tts_voice"] = voice
    _save_settings(settings)

def set_tts_voice_for_follower(follower_id: str, voice: str):
    settings = _load_settings()
    if "follower_voices" not in settings:
        settings["follower_voices"] = {}
    settings["follower_voices"][follower_id] = voice
    
    if settings.get("active_follower") == follower_id:
        settings["tts_voice"] = voice
        os.environ["TTS_VOICE"] = voice
        
    _save_settings(settings)
