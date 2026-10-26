import os
import sys
import time
import requests

# Ensure the parent directory is in sys.path so we can import variables package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from variables.settings import LOCAL_MODELS_URL, DEFAULT_LOCAL_MODEL

_local_models_cache = None
_last_fetch_time = 0.0
_CACHE_TTL = 0.1  # 100ms debounce


def fetch_local_models(force_refresh: bool = False):
    global _local_models_cache, _last_fetch_time
    now = time.time()
    if not force_refresh and _local_models_cache is not None and (now - _last_fetch_time) < _CACHE_TTL:
        return _local_models_cache

    # Primary query to llama-server native /props endpoint
    try:
        response = requests.get("http://127.0.0.1:1234/props", headers={"Content-Type": "application/json"}, timeout=0.05)
        if response.status_code == 200:
            data = response.json()
            model_path = data.get("default_generation_settings", {}).get("model", "")
            if model_path:
                model_name = os.path.basename(model_path)
                _local_models_cache = [{"label": model_name, "value": model_name}]
                _last_fetch_time = now
                return _local_models_cache
    except Exception as e:
        if isinstance(e, requests.exceptions.Timeout):
            pass
        else:
            print(f"[Local LLM] Native models listing offline: {e}")

    # Fallback to standard OpenAI compatibility endpoint /v1/models
    try:
        response = requests.get(LOCAL_MODELS_URL, timeout=0.2)
        response.raise_for_status()
        models_data = response.json()

        models = []
        for item in models_data.get('data', []):
            model_id = item.get('id')
            if model_id:
                models.append({
                    'label': model_id,
                    'value': model_id
                })

        if not models:
            models = [{'label': DEFAULT_LOCAL_MODEL, 'value': DEFAULT_LOCAL_MODEL}]

        _local_models_cache = models
        _last_fetch_time = now
        return models
    except Exception as e:
        if isinstance(e, requests.exceptions.Timeout):
            pass
        else:
            print(f"[Local LLM] Models listing query offline: {e}")
        return []


def is_local_model(model: str) -> bool:
    """Always treats model execution as local without external dependency checks."""
    return True
