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


def get_active_followers() -> list[str]:
    try:
        from core.save_manager import get_active_followers as sm_get_active_followers
        fols = sm_get_active_followers()
        if fols:
            return fols
    except Exception:
        pass

    settings = _load_settings()
    active_fols = settings.get("active_followers")
    if isinstance(active_fols, list) and active_fols:
        return [f for f in active_fols if f and f not in ("game", "none", "solo")][:3]

    single = settings.get("active_follower") or os.getenv("ACTIVE_FOLLOWER") or "riasilmane"
    if single and single not in ("game", "none", "solo"):
        return [single]
    return []


def get_active_follower() -> str:
    fols = get_active_followers()
    return fols[0] if fols else "game"


def set_active_followers(follower_ids: list[str]):
    clean_ids = [f for f in follower_ids if f and f not in ("game", "none", "solo")][:3]
    try:
        from core.save_manager import set_active_followers as sm_set_active_followers
        sm_set_active_followers(clean_ids)
    except Exception:
        pass

    lead_id = clean_ids[0] if clean_ids else "game"
    os.environ["ACTIVE_FOLLOWER"] = lead_id
    settings = _load_settings()
    settings["active_followers"] = clean_ids
    settings["active_follower"] = lead_id
    folders = [os.path.normpath(os.path.join(PARENT_DIR, 'core', 'followers', fid)) for fid in clean_ids if os.path.isdir(os.path.join(PARENT_DIR, 'core', 'followers', fid))]
    if not folders:
        folders = [os.path.normpath(os.path.join(PARENT_DIR, 'core', 'followers', 'game'))]
    settings["folders"] = folders
    _save_settings(settings)


def set_active_follower(follower_id: str):
    if not follower_id or follower_id in ("game", "none", "solo"):
        set_active_followers([])
    else:
        set_active_followers([follower_id])

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
