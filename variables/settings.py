import os
from dotenv import load_dotenv

# Base directory of the LM-Arena application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# Variables directory path
VARIABLES_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration and data file paths
BANNED_WORDS_FILE = os.path.join(VARIABLES_DIR, "banned_words.json")
SAVES_DIR = os.path.join(VARIABLES_DIR, "saves")
ACTIVE_SAVE_FILE = os.path.join(VARIABLES_DIR, "active_save.json")

# Shared directory paths
FOLLOWERS_DIR = os.path.join(BASE_DIR, "core", "followers")
LOREBOOKS_DIR = os.path.join(BASE_DIR, "core", "lorebooks")

# Model and server configurations (Purely offline local LLM)
DEFAULT_LOCAL_MODEL = "local-llm"
DEFAULT_REMOTE_MODEL = "local-llm"
DISABLED_THINKING = {"thinking": {"type": "disabled"}}

# Local server URL and endpoint configuration
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "http://127.0.0.1:8080")
REMOTE_SERVER_URL = LOCAL_SERVER_URL

def get_local_server_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("LOCAL_SERVER_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers

def get_remote_server_headers() -> dict:
    return get_local_server_headers()

def is_thinking_enabled() -> bool:
    env_val = os.getenv("THINKING_ENABLED")
    if env_val is not None:
        return env_val.lower() in ("true", "1", "yes")
    return False

# Dynamically derive models URL from LOCAL_SERVER_URL
try:
    from urllib.parse import urlparse
    _parsed = urlparse(LOCAL_SERVER_URL)
    if _parsed.path.endswith('/chat/completions'):
        _base_path = _parsed.path.rsplit('/chat/completions', 1)[0]
    else:
        _base_path = '/v1'
    LOCAL_MODELS_URL = f"{_parsed.scheme}://{_parsed.netloc}{_base_path}/models"
except Exception:
    LOCAL_MODELS_URL = "http://127.0.0.1:8080/v1/models"

# ComfyUI Image Generation configurations
COMFYUI_SERVER_URL = os.getenv("COMFYUI_SERVER_URL", "http://127.0.0.1:8188")
_env_comfyui_dir = os.getenv("COMFYUI_DIR")
COMFYUI_DIR = _env_comfyui_dir.strip() if (_env_comfyui_dir and _env_comfyui_dir.strip()) else os.path.normpath(os.path.join(BASE_DIR, "..", "ComfyUI"))
COMFYUI_CHECKPOINT = os.getenv("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors")
COMFYUI_VAE = os.getenv("COMFYUI_VAE", "sdxl_vae.safetensors")

# Centralized Models directory hierarchy & Logs
LOGS_DIR = os.path.join(BASE_DIR, "logs")
MODELS_DIR = os.path.join(BASE_DIR, "models")
LLM_MODELS_DIR = os.path.join(MODELS_DIR, "llm")
CHECKPOINTS_DIR = os.path.join(MODELS_DIR, "checkpoints")
LORAS_DIR = os.path.join(MODELS_DIR, "loras")
VAE_DIR = os.path.join(MODELS_DIR, "vae")

for _dir in (MODELS_DIR, LLM_MODELS_DIR, CHECKPOINTS_DIR, LORAS_DIR, VAE_DIR, FOLLOWERS_DIR, LOREBOOKS_DIR, SAVES_DIR, LOGS_DIR):
    os.makedirs(_dir, exist_ok=True)

