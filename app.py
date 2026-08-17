import os
import time
import shutil
import json
import re
import importlib
import traceback
import threading
import uuid

# Automate copying of default .env configuration if it doesn't exist
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '.env')
if not os.path.exists(env_path):
    example_path = os.path.join(base_dir, '.env.example')
    if os.path.exists(example_path):
        try:
            shutil.copy(example_path, env_path)
            print(f">>> Automatically copied {example_path} to {env_path}")
        except Exception as e:
            print(f"Error copying default .env configuration: {e}")

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response, make_response
import asyncio
from functools import wraps
from runner_interface import OpenSourceRunner

# Load environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

app = Flask(__name__)

_cached_active_program = None
_cached_active_user = None

def init_runner():
    global runner
    runner = OpenSourceRunner(app_name="LM-Arena")
    print(">>> Starting LM-Arena using decoupled OPEN-SOURCE Runner backend!")

_prewarm_started = False
_prewarm_lock = threading.Lock()

@app.before_request
def start_prewarm_on_first_request():
    global _prewarm_started
    if not _prewarm_started:
        with _prewarm_lock:
            if not _prewarm_started:
                _prewarm_started = True
                threading.Thread(target=prewarm_caches, daemon=True).start()

@app.before_request
def check_program_change():
    global _cached_active_program, _cached_active_user
    from utils.program import get_active_program, get_active_user
    current_program = get_active_program()
    current_user = get_active_user()
            
    program_changed = current_program != _cached_active_program
    user_changed = current_user != _cached_active_user
    
    if program_changed or user_changed:
        if program_changed:
            _cached_active_program = current_program
            os.environ["ACTIVE_PROGRAM"] = current_program
            try:
                from variables import PROGRAMS_DIR
                program_path = os.path.join(PROGRAMS_DIR, current_program)
                if os.path.isdir(program_path):
                    # Setup portraits directory and perform migration from legacy folder if needed
                    portraits_dir = os.path.join(program_path, 'portraits')
                    legacy_dir = os.path.join(program_path, 'sel' + 'fies')
                    if os.path.exists(legacy_dir) and not os.path.exists(portraits_dir):
                        try:
                            os.rename(legacy_dir, portraits_dir)
                            print(f"Migrated legacy folder to portraits for program {current_program}")
                        except Exception as ex:
                            print(f"Error migrating legacy folder for program {current_program}: {ex}")
                    os.makedirs(portraits_dir, exist_ok=True)
            except Exception as ex:
                print(f"Error preparing portraits directory for active program: {ex}")
        if user_changed:
            _cached_active_user = current_user
            
        try:
            reload_program_state()
            print(f">>> Dynamic check loaded new program consciousness (Program: '{current_program}', User Profile: '{current_user}')")
        except Exception as e:
            print(f"Error dynamically reloading program/user: {e}")

@app.after_request
def add_cache_control_headers(response):
    response.headers['Cache-Control'] = 'no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# Initialize active program and active user cache
try:
    from utils.program import get_active_program, get_active_user
    _cached_active_program = get_active_program()
    _cached_active_user = get_active_user()
except Exception as e:
    print(f"Error initializing active program: {e}")
    raise

def prewarm_caches():
    print(">>> Pre-warming backend caches in background...")
    # Gemini models cache prewarming removed to favor decoupled remote configs
        
    try:
        # Prewarm local models list
        from utils.models import fetch_local_models
        fetch_local_models(force_refresh=True)
    except Exception as e:
        print(f"Error prewarming local models: {e}")
        
    try:
        # Prewarm server status
        from utils.local_llm_manager import check_status, check_installed
        llm_already_online = check_status(force_refresh=True)
        check_installed()
    except Exception as e:
        print(f"Error prewarming Local LLM server status: {e}")
        llm_already_online = False

    # Auto-start disabled: Local LLM and ComfyUI are manual only.
    # Use the UI controls to start each server when needed.
    print(">>> Local LLM auto-start disabled (manual only).")
    print(">>> ComfyUI auto-start disabled (manual only).")

    print(">>> Backend caches pre-warmed successfully!")

# Initialize the dynamic runner based on configuration
init_runner()


def reload_program_state():
    """Reload program config, reinitialize the runner, and sync active save session."""
    from core import program_config
    importlib.reload(program_config)
    init_runner()
    if hasattr(runner, '_load_session_from_disk'):
        runner._load_session_from_disk('default')


def load_theme(program_id):
    """Load theme.json for a program, returning the parsed dict or None."""
    theme_path = os.path.join(base_dir, "core", "programs", program_id, "theme.json")
    if os.path.exists(theme_path):
        try:
            with open(theme_path, "r", encoding="utf-8") as tf:
                return json.load(tf)
        except Exception as e:
            print(f"Error loading theme for {program_id}: {e}")
    return None


def load_temperature():
    """Read temperature from project settings, locked to 0.85 for LM-Arena balance."""
    from variables import VARIABLES_DIR
    settings_path = os.path.join(VARIABLES_DIR, "project_settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f).get("temperature", 0.85)
        except Exception:
            pass
    return 0.85


def find_image_sidecar_json(image_filename, active_program):
    """Locate the sidecar .json for an image, scanning active then all programs."""
    png_path = os.path.normpath(
        os.path.join(base_dir, 'core', 'programs', active_program, 'portraits', image_filename)
    )
    json_path = png_path.rsplit('.', 1)[0] + '.json'
    if os.path.exists(json_path):
        return json_path
    from variables import PROGRAMS_DIR
    if os.path.exists(PROGRAMS_DIR):
        for prog in os.listdir(PROGRAMS_DIR):
            candidate = os.path.normpath(
                os.path.join(PROGRAMS_DIR, prog, 'portraits', image_filename)
            )
            candidate_json = candidate.rsplit('.', 1)[0] + '.json'
            if os.path.exists(candidate_json):
                return candidate_json
    return None


def sanitize_response(response_text, session_id, program_msg_id):
    """Apply banned words filter and update persisted message if sanitized."""
    from utils.banned_words import sanitize_text
    sanitized = sanitize_text(response_text)
    if sanitized != response_text:
        print(f"[BANNED WORDS] Sanitized response in session {session_id}")
        if program_msg_id:
            asyncio.run(runner.update_message_text(session_id, program_msg_id, sanitized))
    return sanitized





# --- SECURE OPTIONAL AUTHENTICATION DECORATOR ---
def check_auth(username, password):
    return username == os.getenv("AUTH_USER") and password == os.getenv("AUTH_PASS")

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_user = os.getenv("AUTH_USER")
        auth_pass = os.getenv("AUTH_PASS")
        # Only enforce basic auth if credentials are set in the environment (.env)
        if auth_user and auth_pass:
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    import socket
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Dummy connection to trigger local IP interface detection
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    
    tts_auto_speak = os.getenv("TTS_AUTO_SPEAK", "false").lower() == "true"
    tts_provider = os.getenv("TTS_PROVIDER", "local").lower()
    active_program = os.getenv("ACTIVE_PROGRAM", "sebile")
    theme = load_theme(active_program)

    from utils.program import get_active_user, get_player_name
    active_user = get_active_user()
    if os.getenv("AUTH_USER") and request.authorization and active_user == "eternal_champion":
        # If Basic Auth is active, default active user to authenticated user
        active_user = request.authorization.username

    user_name = get_player_name()

    from flask import make_response
    from core.program_config import get_program_greeting, replace_placeholders
    welcome_message = replace_placeholders(get_program_greeting(), user_name=user_name)
    response = make_response(render_template('index.html', local_ip=local_ip, tts_auto_speak=tts_auto_speak, tts_provider=tts_provider, active_program=active_program, theme=theme, active_user=active_user, user_name=user_name, welcome_message=welcome_message))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/manifest.json')
def serve_manifest():
    from core.program_config import program_name
    import json
    try:
        with open('manifest.json', 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        manifest_data['name'] = f"LM-Arena"
        manifest_data['short_name'] = f"LM-Arena"
        manifest_data['description'] = f"The Elder Scrolls: Arena — LLM Text Adventure"
        return jsonify(manifest_data)
    except Exception:
        return send_file('manifest.json', mimetype='application/json')

@app.route('/service-worker.js')
def serve_service_worker():
    return send_file('service-worker.js', mimetype='application/javascript')

@app.route('/app_icon.png')
def app_icon():
    response = send_file('static/img/app_icon.png')
    from flask import make_response
    res = make_response(response)
    res.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return res

@app.route('/profile.png')
def profile_png():
    from utils.program import get_active_program
    active_program = get_active_program()
    path_png = os.path.join('core', 'programs', active_program, 'portraits', 'profile.png')
    if os.path.exists(path_png):
        response = send_file(path_png)
        from flask import make_response
        res = make_response(response)
        res.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return res
    else:
        return "Profile image not found", 404


@app.route('/programs/<program_id>/profile.png')
def program_profile_png(program_id):
    import re
    if not re.match(r'^[a-zA-Z0-9_\-]+$', program_id):
        return "Invalid program ID", 400
    path_png = os.path.join('core', 'programs', program_id, 'portraits', 'profile.png')
    if os.path.exists(path_png):
        response = send_file(path_png)
        from flask import make_response
        res = make_response(response)
        res.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return res
    else:
        return "Profile image not found", 404



@app.route('/api/programs/profile_picture/save', methods=['POST'])
@requires_auth
def save_profile_picture():
    try:
        from variables import PROGRAMS_DIR
        from utils.program import get_active_program
        import base64
        import re
        
        data = request.get_json(silent=True) or {}
        cropped_image_base64 = data.get('cropped_image')
        if not cropped_image_base64:
            return jsonify({'error': 'No cropped_image data provided'}), 400
            
        program_id = data.get('program_id') or get_active_program()
        portraits_dir = os.path.join(PROGRAMS_DIR, program_id, 'portraits')
        os.makedirs(portraits_dir, exist_ok=True)
        dest_path = os.path.join(portraits_dir, 'profile.png')
        
        # Remove base64 header if present (e.g., data:image/png;base64,)
        if ',' in cropped_image_base64:
            base64_data = cropped_image_base64.split(',', 1)[1]
        else:
            base64_data = cropped_image_base64
            
        image_bytes = base64.b64decode(base64_data)
        print(f"[PROFILE SAVE] program={program_id}, dataUrl length={len(cropped_image_base64)}, base64 length={len(base64_data)}, decoded bytes={len(image_bytes)}, dest={dest_path}")
        with open(dest_path, 'wb') as f:
            f.write(image_bytes)
            
        return jsonify({'status': 'success', 'message': 'Profile picture cropped and saved successfully.'})
    except Exception as e:
        print(f"Error saving profile picture: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/programs/profile_picture/crop', methods=['POST'])
@requires_auth
def crop_profile_picture():
    """Server-side crop: receives source image path and crop coordinates, uses PIL to crop and resize."""
    try:
        from variables import PROGRAMS_DIR
        from utils.program import get_active_program
        from PIL import Image
        
        data = request.get_json(silent=True) or {}
        source_image = data.get('source_image', '')
        x = int(data.get('x', 0))
        y = int(data.get('y', 0))
        w = int(data.get('width', 0))
        h = int(data.get('height', 0))
        
        if not source_image or w <= 0 or h <= 0:
            return jsonify({'error': 'Invalid crop parameters'}), 400
        
        program_id = data.get('program_id') or get_active_program()
        program_dir = os.path.join(PROGRAMS_DIR, program_id)
        
        # Resolve source image path from the URL path to a local file path
        # Source paths arrive as /images/portraits/xyz.png or /images/xyz.png
        if source_image.startswith('/images/'):
            relative_path = source_image[len('/images/'):]
            source_path = os.path.normpath(os.path.join(program_dir, relative_path))
        elif source_image.startswith('/profile.png'):
            source_path = os.path.normpath(os.path.join(program_dir, 'portraits', 'profile.png'))
        else:
            return jsonify({'error': 'Unsupported image path'}), 400
        
        if not os.path.exists(source_path):
            return jsonify({'error': f'Source image not found: {source_image}'}), 404
        
        # Crop and resize with PIL
        with Image.open(source_path) as img:
            # Clamp crop coordinates to image bounds
            img_w, img_h = img.size
            x = max(0, min(x, img_w))
            y = max(0, min(y, img_h))
            w = min(w, img_w - x)
            h = min(h, img_h - y)
            
            cropped = img.crop((x, y, x + w, y + h))
            cropped = cropped.resize((256, 256), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (handles RGBA, palette, etc.)
            if cropped.mode not in ('RGB', 'RGBA'):
                cropped = cropped.convert('RGBA')
        
        portraits_dir = os.path.join(program_dir, 'portraits')
        os.makedirs(portraits_dir, exist_ok=True)
        dest_path = os.path.join(portraits_dir, 'profile.png')
        cropped.save(dest_path, 'PNG')
        
        print(f"[PROFILE CROP] program={program_id}, source={source_path}, crop=({x},{y},{w},{h}), dest={dest_path}")
        return jsonify({'status': 'success', 'message': 'Profile picture cropped and saved successfully.'})
    except Exception as e:
        print(f"Error cropping profile picture: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/sound/<path:filename>')
def serve_sound(filename):
    sound_dir = os.path.join(base_dir, 'sound')
    return send_from_directory(sound_dir, filename)
 
@app.route('/images/<path:filename>')
@requires_auth
def serve_image(filename):
    static_img_dir = os.path.join(base_dir, 'static', 'img')
    if os.path.exists(os.path.join(static_img_dir, filename)):
        return send_from_directory(static_img_dir, filename)

    try:
        from utils.program import get_active_program
        active_program = get_active_program()
    except Exception:
        active_program = os.getenv("ACTIVE_PROGRAM", "ria_silmane")
    program_dir = os.path.join('core', 'programs', active_program)
    if os.path.exists(os.path.join(program_dir, filename)):
        return send_from_directory(program_dir, filename)
    return send_from_directory(static_img_dir, filename)


@app.route('/api/get_image_prompt', methods=['GET'])
@requires_auth
def get_image_prompt():
    image_url = request.args.get('image_url')
    if not image_url:
        return jsonify({'error': 'Missing image_url'}), 400
        
    if "://" in image_url:
        from urllib.parse import urlparse
        image_url = urlparse(image_url).path
        
    try:
        import json
        from utils.program import get_active_program
        active_program = get_active_program()
        
        if image_url.startswith('/images/'):
            img_subpath = image_url[8:]
        else:
            img_subpath = os.path.basename(image_url)
            
        # Security: keep filename only to prevent directory traversal
        img_subpath = os.path.basename(img_subpath)
        json_path = find_image_sidecar_json(img_subpath, active_program)

        if json_path and os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                prompt = meta.get('prompt', '')
                return jsonify({'status': 'success', 'prompt': prompt})
        else:
            return jsonify({'status': 'success', 'prompt': ''})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/proactive_action', methods=['POST'])
@requires_auth
def proactive_action():
    session_id = request.json.get('session_id', 'default')
    selected_model = request.json.get('model')
    
    try:
        import os
        import json
        from utils.program import get_active_program
        from variables import PROGRAMS_DIR
        
        active_program = get_active_program()
        program_path = os.path.join(PROGRAMS_DIR, active_program)
        
        name = "Program"
        description = ""
        personality = ""
        scenario = ""
        
        # Read active program JSON config
        for filename in [f"{active_program}.json", "character_profile.json"]:
            json_path = os.path.join(program_path, filename)
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        name = data.get('name', name)
                        op = data.get('operation', {})
                        description = op.get('description', '')
                        personality = op.get('personality', '')
                        scenario = op.get('scenario', '')
                except Exception as ex:
                    print(f"Error reading program config for proactive action: {ex}")
                    
        # Get active player name
        from utils.program import get_player_name
        user_display_name = get_player_name()

        # Load session history
        chat_history = asyncio.run(runner.get_history(session_id))
        
        # Limit proactive messages to one: do not send another if one was already sent during this idle period
        for msg in reversed(chat_history):
            if msg.get('role') == 'user':
                break
            if msg.get('role') == 'program' and msg.get('is_proactive'):
                print(f"[PROACTIVE] A proactive message was already sent since the last user message. Skipping.")
                return jsonify({
                    'status': 'success',
                    'type': 'skipped',
                    'reason': 'A proactive message was already sent since the last user message.'
                })
        
        # Generate history context string
        history_context = ""
        for msg in chat_history[-10:]:
            role = msg.get('role', 'unknown')
            text = msg.get('text') or msg.get('content') or ""
            if role in ('user', 'program'):
                speaker = user_display_name if role == 'user' else name
                history_context += f"{speaker}: {text}\n"
                
        # Define LLM prompt for Gameplay Tip / Lore Note
        prompt = f"""You are the game master and lore assistant for The Elder Scrolls: Arena (LM-Arena).
Active Companion: {name}
Scenario: {scenario}

Recent Conversation History:
{history_context}

The player ({user_display_name}) has been idle for a moment.
Based on the current scenario, location, and conversation context, generate a helpful, concise GAMEPLAY TIP or RELEVANT LORE NOTE (1-2 sentences).
Explain an interesting gameplay mechanic (such as spell absorption, resting safety, material immunities, calendar holidays, silver weapons, or combat stamina) or share authentic Tamrielic lore.

You must return a valid JSON object matching the following schema:
{{
  "type": "tip",
  "content": "the actual tip or lore note text"
}}
"""

        # Call the LLM
        from utils.models import is_local_model
        is_local = is_local_model(selected_model) if selected_model else True
        raw_response = None
        
        if is_local:
            import requests
            from variables import REMOTE_SERVER_URL, get_remote_server_headers
            target_model = selected_model if (selected_model and selected_model != 'local-llm') else os.getenv("LOCAL_MODEL_NAME")
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 320
            }
            if target_model:
                payload["model"] = target_model
            try:
                headers = get_remote_server_headers()
                r = requests.post(REMOTE_SERVER_URL, json=payload, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    raw_response = r.json()['choices'][0]['message']['content'].strip()
            except Exception as e:
                # Local LLM is offline - fallback to remote cloud model if available
                api_key = os.getenv("REMOTE_API_KEY")
                remote_cloud_url = os.getenv("REMOTE_CLOUD_URL")
                if api_key and remote_cloud_url:
                    try:
                        target_model = os.getenv("REMOTE_MODEL", "gemini-3.1-flash-lite")
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}"
                        }
                        payload["model"] = target_model
                        r_cloud = requests.post(remote_cloud_url, json=payload, headers=headers, timeout=15.0)
                        if r_cloud.status_code == 200:
                            raw_response = r_cloud.json()['choices'][0]['message']['content'].strip()
                    except Exception as ce:
                        pass
        else:
            api_key = os.getenv("REMOTE_API_KEY")
            remote_cloud_url = os.getenv("REMOTE_CLOUD_URL")
            if api_key and remote_cloud_url:
                import requests
                target_model = selected_model if selected_model else os.getenv("REMOTE_MODEL", "gemini-3.1-flash-lite")
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                payload = {
                    "model": target_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 320,
                    "response_format": {"type": "json_object"},
                    "thinking": {"type": "disabled"}
                }
                try:
                    r = requests.post(remote_cloud_url, json=payload, headers=headers, timeout=30.0)
                    if r.status_code == 200:
                        raw_response = r.json()['choices'][0]['message']['content'].strip()
                    else:
                        print(f"[PROACTIVE] Remote cloud query failed with status {r.status_code}: {r.text}")
                except Exception as e:
                    print(f"[PROACTIVE] Remote cloud query failed: {e}")
                    
        if not raw_response:
            return jsonify({'status': 'idle', 'message': 'No proactive action taken'}), 200
            
        # Parse output
        action_type = "tip"
        content = ""
        
        try:
            # Clean JSON markdown formatting if present
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            parsed = json.loads(cleaned)
            action_type = parsed.get("type", "tip").lower()
            content = parsed.get("content", "").strip()
        except Exception as e:
            print(f"[PROACTIVE] JSON parsing failed: {e}. Raw: {raw_response}")
            action_type = "tip"
            content = raw_response
            
        return jsonify({
            'status': 'success',
            'type': 'tip',
            'content': content
        })
            
    except Exception as e:
        print(f"Error in proactive_action route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
@requires_auth
def history():
    session_id = request.args.get('session_id', 'default')
    try:
        chat_history = asyncio.run(runner.get_history(session_id))
        
        from utils.program import get_player_name
        user_name = get_player_name()

        from core.program_config import program_name, get_program_greeting, replace_placeholders
        welcome_message = replace_placeholders(get_program_greeting(), user_name=user_name)
        active_program = os.environ.get("ACTIVE_PROGRAM", "sebile")
        
        theme = load_theme(active_program)

        return jsonify({
            'history': chat_history,
            'character_name': program_name,
            'user_name': user_name,
            'active_program': active_program,
            'theme': theme,
            'welcome_message': welcome_message
        })
    except Exception as e:
        print(f"Error getting history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload_media', methods=['POST'])
@requires_auth
def upload_media():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Ensure size validation
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0) # Reset stream pointer

    # Restrict videos to 15MB
    if file.mimetype and file.mimetype.startswith('video/'):
        if file_length > 15 * 1024 * 1024:
            return jsonify({'error': 'Video file exceeds the 15MB limit'}), 413
    else:
        # Enforce a general limit for other files (e.g., 20MB)
        if file_length > 20 * 1024 * 1024:
            return jsonify({'error': 'File exceeds the 20MB limit'}), 413

    import uuid
    import time
    from werkzeug.utils import secure_filename

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"upload_{int(time.time())}_{uuid.uuid4().hex}{ext}"

    active_program = os.getenv("ACTIVE_PROGRAM", "sebile")
    uploads_dir = os.path.normpath(os.path.join('core', 'programs', active_program, 'uploads'))
    os.makedirs(uploads_dir, exist_ok=True)
    
    local_path = os.path.join(uploads_dir, unique_name)
    file.save(local_path)

    return jsonify({'file_path': f'/images/uploads/{unique_name}'})

@app.route('/chat', methods=['POST'])
@requires_auth
def chat():
    user_message = request.json.get('message')
    image_data = request.json.get('image_data')
    image_mime = request.json.get('image_mime')
    media_path = request.json.get('media_path')
    session_id = request.json.get('session_id', 'default')
    selected_model = request.json.get('model')
    is_voice_call = request.json.get('is_voice_call', False)

    import tools
    tools.current_session_id.set(session_id)
    with tools.session_tool_calls_lock:
        tools.session_tool_calls[session_id] = []

    from runner_interface import cancelled_sessions, voice_call_sessions
    cancelled_sessions.discard(session_id)
    if is_voice_call:
        voice_call_sessions.add(session_id)
        
    start_time = time.time()

    try:
        msg_id = request.json.get('msg_id')
        response_text, tool_calls, user_msg_id, program_msg_id = asyncio.run(
            runner.run_async(
                session_id=session_id,
                new_message_text=user_message,
                image_data=image_data,
                image_mime=image_mime,
                model=selected_model,
                media_path=media_path,
                msg_id=msg_id
            )
        )
        duration = round(time.time() - start_time, 1)
        
        # Apply banned words filter to output response
        response_text = sanitize_response(response_text, session_id, program_msg_id)

        chat_history = asyncio.run(runner.get_history(session_id))
        
        # Align timestamp with stored program message
        program_timestamp = None
        if program_msg_id:
            for msg in reversed(chat_history):
                if msg.get('id') == program_msg_id:
                    program_timestamp = msg.get('timestamp')
                    break
            
        return jsonify({
            'response': response_text,
            'tool_calls': tool_calls,
            'timestamp': program_timestamp or time.time(),
            'duration': duration,
            'user_msg_id': user_msg_id,
            'program_msg_id': program_msg_id
        })
    except asyncio.CancelledError:
        print(f"[CANCEL] Chat generation cancelled for session {session_id}")
        return jsonify({
            'cancelled': True,
            'status': 'cancelled'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error occurred in chat: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        from runner_interface import cancelled_sessions, voice_call_sessions
        cancelled_sessions.discard(session_id)
        voice_call_sessions.discard(session_id)

@app.route('/edit', methods=['POST'])
@requires_auth
def edit():
    session_id = request.json.get('session_id', 'default')
    msg_id = request.json.get('msg_id')
    new_text = request.json.get('new_text') # None means reroll (use original text)
    selected_model = request.json.get('model')
    force_offload = request.json.get('force_offload', False)
    print(f"[EDIT ROUTE] session_id={session_id}, msg_id={msg_id}, new_text={repr(new_text)}, model={selected_model}, force_offload={force_offload}", flush=True)

    import tools
    tools.current_session_id.set(session_id)
    with tools.session_tool_calls_lock:
        tools.session_tool_calls[session_id] = []

    from runner_interface import cancelled_sessions
    cancelled_sessions.discard(session_id)
    start_time = time.time()

    try:
        response_text, tool_calls, user_msg_id, program_msg_id = asyncio.run(
            runner.edit_turn(
                session_id=session_id,
                msg_id=msg_id,
                new_text=new_text,
                model=selected_model,
                force_offload=force_offload
            )
        )
        duration = round(time.time() - start_time, 1)
        print(f"[EDIT ROUTE DONE] len(response_text)={len(response_text)}, tools={len(tool_calls)}, duration={duration}s", flush=True)
        
        # Apply banned words filter to output response
        response_text = sanitize_response(response_text, session_id, program_msg_id)

        chat_history = asyncio.run(runner.get_history(session_id))

        # Align timestamp with stored program message
        program_timestamp = None
        if program_msg_id:
            for msg in reversed(chat_history):
                if msg.get('id') == program_msg_id:
                    program_timestamp = msg.get('timestamp')
                    break

        return jsonify({
            'response': response_text,
            'tool_calls': tool_calls,
            'timestamp': program_timestamp or time.time(),
            'duration': duration,
            'user_msg_id': user_msg_id,
            'program_msg_id': program_msg_id
        })
    except asyncio.CancelledError:
        print(f"[CANCEL] Edit generation cancelled for session {session_id}")
        return jsonify({
            'cancelled': True,
            'status': 'cancelled'
        })
    except Exception as e:
        print(f"Error occurred during edit: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        from runner_interface import cancelled_sessions
        cancelled_sessions.discard(session_id)

def generate_impersonated_message(session_id, user_profile, model, user_input=""):
    # Retrieve history
    chat_history = asyncio.run(runner.get_history(session_id))
    
    temperature = load_temperature()
            
    # Format only the most recent history turns to keep token count low and prevent context overflow
    recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
    history_text = ""
    for msg in recent_history:
        role = "User" if msg.get('role') == 'user' else "Program"
        history_text += f"{role}: {msg.get('text', '')}\n"
    
    from core.program_config import load_user_instructions, replace_placeholders
    from utils.program import get_active_user
    from engine.character import load_character, get_character_context

    char_context = ""
    try:
        active_user = get_active_user()
        sheet = load_character(active_user)
        if sheet:
            char_context = get_character_context(sheet)
            world = sheet.get("world", {})
            loc = world.get("current_location", "Imperial Dungeon")
            prov = world.get("current_province", "Cyrodiil")
            char_context += f"\nCurrent Location: {loc}, {prov}"
    except Exception as e:
        print(f"Error compiling character sheet for suggestion: {e}")

    user_rel_context = ""
    try:
        user_rel_context = load_user_instructions().strip()
    except Exception as e:
        print(f"Error loading user profile context for suggestion: {e}")

    full_profile_block = ""
    if user_profile and user_profile.strip():
        full_profile_block += f"Custom Input Profile:\n{user_profile.strip()}\n\n"
    if char_context:
        full_profile_block += f"{char_context}\n\n"
    if user_rel_context:
        full_profile_block += f"{user_rel_context}\n"

    if not full_profile_block.strip():
        full_profile_block = "Character: Eternal Champion, Adventurer in Tamriel."

    seed_text = (user_input or "").strip()
    
    system_instruction = (
        "Generate {{user}}'s next action in the Elder Scrolls roleplay.\n"
        "- Perspective: Always write in the FIRST PERSON ('I', 'my') as {{user}}.\n"
        "- Tense: Strict PRESENT TENSE (e.g. 'I draw my dagger...', 'I examine the stone runes...').\n"
        "- Format: *Italics* for physical actions and plain text for spoken dialogue.\n"
        "- Grounding: Use clear, direct, immersive fantasy actions. Avoid surreal metaphors, modern idioms, or echoing awkward phrasing.\n"
        "- Restraint: Focus purely on {{user}}'s initiative and intent. Avoid narrating outcomes, hits, or DM-level world changes."
    )
    
    if seed_text and len(seed_text.split()) <= 15:
        # Short player guidance / seed intent
        prompt = (
            f"### USER CHARACTER PROFILE & STATUS\n"
            f"{replace_placeholders(full_profile_block)}\n\n"
            f"### RECENT CHAT HISTORY\n"
            f"{replace_placeholders(history_text)}\n\n"
            f"### PLAYER INTENT\n"
            f"{replace_placeholders(seed_text)}\n\n"
            f"Generate a natural first-person present-tense action for {{user}} carrying out this intent (avoid narrating outcomes):"
        )
    else:
        # Fresh action or reroll alternative
        prompt = (
            f"### USER CHARACTER PROFILE & STATUS\n"
            f"{replace_placeholders(full_profile_block)}\n\n"
            f"### RECENT CHAT HISTORY\n"
            f"{replace_placeholders(history_text)}\n\n"
            f"Generate a fresh, natural first-person present-tense action for {{user}} responding to the current situation (avoid narrating outcomes):"
        )
    
    try:
        from utils.banned_words import get_banned_words_directive, sanitize_text
        banned_dir = get_banned_words_directive()
        if banned_dir:
            system_instruction += f"\n{banned_dir}"
    except Exception:
        pass

    # Delegate entirely to the runner's provider-agnostic generator
    try:
        raw_msg = asyncio.run(runner.generate_impersonation(prompt, system_instruction, model, temperature))
        try:
            from utils.banned_words import sanitize_text
            return sanitize_text(raw_msg)
        except Exception:
            return raw_msg
    except Exception as e:
        print(f"Error generating impersonated message via runner: {e}")
        raise

@app.route('/api/generate_user_message', methods=['POST'])
@requires_auth
def generate_user_message():
    session_id = request.json.get('session_id', 'default')
    model = request.json.get('model')
    user_profile = request.json.get('user_profile', '').strip()
    user_input = request.json.get('current_input', request.json.get('user_input', '')).strip()
        
    try:
        generated_msg = generate_impersonated_message(session_id, user_profile, model, user_input=user_input)
        return jsonify({'status': 'success', 'message': generated_msg})
    except Exception as e:
        print(f"Error generating impersonated user message: {e}")
        return jsonify({'error': str(e)}), 500

def generate_player_skill_check_action(session_id, skill_name, attribute_name, dc, reason, model, is_flat_roll=False):
    import random
    from utils.program import get_active_user
    from engine.character import load_character, get_character_context
    from engine.mechanics import roll_check

    active_user = get_active_user()
    sheet = load_character(active_user)
    attributes = sheet.get("attributes", {})

    if is_flat_roll:
        roll_val = random.randint(1, 20)
        if roll_val == 20:
            degree = "critical"
        elif roll_val == 1:
            degree = "fumble"
        elif roll_val >= 10:
            degree = "success"
        else:
            degree = "failure"
        roll_res = {
            "roll": roll_val,
            "modifier": 0,
            "total": roll_val,
            "dc": 10,
            "degree": degree,
            "success": roll_val >= 10
        }
        attr_val = 50
        dc_val = 10
    else:
        attr_val = 50
        for k, v in attributes.items():
            if k.lower() == str(attribute_name).strip().lower():
                try:
                    attr_val = int(v)
                except Exception:
                    attr_val = 50
                break

        try:
            dc_val = int(dc)
        except Exception:
            dc_val = 15

        roll_res = roll_check(attribute_name, attr_val, dc_val)

    chat_history = asyncio.run(runner.get_history(session_id))
    temperature = load_temperature()

    recent_history = chat_history[-2:] if len(chat_history) > 2 else chat_history
    history_text = ""
    for msg in recent_history:
        role = "User" if msg.get('role') == 'user' else "Program"
        history_text += f"{role}: {msg.get('text', '')}\n"

    char_context = ""
    try:
        char_context = get_character_context(sheet)
    except Exception as e:
        print(f"Error getting character context for skill check: {e}")

    system_instruction = (
        "Generate {{user}}'s immediate reaction in FIRST PERSON PRESENT TENSE.\n"
        f"1 concise *italicized* narrative sentence in present tense (e.g. 'I slip on the damp stone...', 'I catch my balance...') matching the {roll_res['degree']} outcome."
    )
    try:
        from utils.banned_words import get_banned_words_directive, sanitize_text
        banned_dir = get_banned_words_directive()
        if banned_dir:
            system_instruction += f"\n{banned_dir}"
    except Exception:
        pass

    if is_flat_roll:
        prompt = (
            f"### CHARACTER CONTEXT\n"
            f"{char_context}\n\n"
            f"### FLAT ACTION ROLL CONTEXT\n"
            f"- Flat d20 Roll: {roll_res['roll']} (Outcome: {roll_res['degree'].upper()})\n\n"
            f"### RECENT CHAT HISTORY\n"
            f"{history_text}\n\n"
            f"Generate a single first person present tense narrative sentence describing {{user}}'s immediate action reflecting this {roll_res['degree']} outcome:"
        )
    else:
        prompt = (
            f"### CHARACTER CONTEXT\n"
            f"{char_context}\n\n"
            f"### SKILL CHECK CONTEXT\n"
            f"- Skill: {skill_name}\n"
            f"- Attribute: {attribute_name} (Value: {attr_val}, Modifier: {'+' if roll_res['modifier'] >= 0 else ''}{roll_res['modifier']})\n"
            f"- Difficulty Class: DC {dc_val}\n"
            f"- Roll Result: d20 rolled {roll_res['roll']} + {roll_res['modifier']} = {roll_res['total']} vs DC {dc_val}\n"
            f"- Degree: {roll_res['degree'].upper()} ({'Success' if roll_res['success'] else 'Failure'})\n"
            f"- Context: {reason}\n\n"
            f"### RECENT CHAT HISTORY\n"
            f"{history_text}\n\n"
            f"Generate a single first person present tense narrative sentence describing {{user}}'s immediate action reflecting this {roll_res['degree']} outcome:"
        )

    action_text = asyncio.run(runner.generate_impersonation(prompt, system_instruction, model, temperature))
    action_text = action_text.strip().replace('"', '')
    try:
        from utils.banned_words import sanitize_text
        action_text = sanitize_text(action_text)
    except Exception:
        pass

    # Return pure narrative action without visible bracketed roll formulas
    formatted_message = action_text

    return {
        "roll_res": roll_res,
        "action_text": action_text,
        "formatted_message": formatted_message
    }

@app.route('/api/execute_player_skill_check', methods=['POST'])
@requires_auth
def execute_player_skill_check():
    session_id = request.json.get('session_id', 'default')
    skill_name = request.json.get('skill_name', 'Agility')
    attribute_name = request.json.get('attribute_name', 'Agility')
    dc = request.json.get('dc', 15)
    reason = request.json.get('reason', '')
    model = request.json.get('model')
    is_flat_roll = request.json.get('is_flat_roll', False)

    try:
        res = generate_player_skill_check_action(session_id, skill_name, attribute_name, dc, reason, model, is_flat_roll=is_flat_roll)
        return jsonify({
            'status': 'success',
            'roll_res': res['roll_res'],
            'action_text': res['action_text'],
            'formatted_message': res['formatted_message']
        })
    except Exception as e:
        print(f"Error executing player skill check: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/update_message', methods=['POST'])
@requires_auth
def update_message():
    session_id = request.json.get('session_id', 'default')
    msg_id = request.json.get('msg_id')
    new_text = request.json.get('new_text')
    
    if not msg_id or new_text is None:
        return jsonify({'error': 'msg_id and new_text are required'}), 400

    try:
        success = asyncio.run(runner.update_message_text(session_id, msg_id, new_text))
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Message not found'}), 404
    except Exception as e:
        print(f"Error updating message text: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete', methods=['POST'])
@requires_auth
def delete_message():
    session_id = request.json.get('session_id', 'default')
    msg_id = request.json.get('msg_id')

    if not msg_id:
        return jsonify({'error': 'msg_id is required'}), 400

    try:
        success = asyncio.run(runner.delete_message_at(session_id, msg_id))
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Message not found'}), 404
    except Exception as e:
        print(f"Error deleting message {msg_id}: {e}")
        return jsonify({'error': str(e)}), 500





@app.route('/reset', methods=['POST'])
@requires_auth
def reset():
    session_id = request.json.get('session_id', 'default')
    try:
        asyncio.run(runner.reset_session(session_id))
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error resetting session {session_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_image', methods=['POST'])
@requires_auth
def delete_image():
    session_id = request.json.get('session_id', 'default')
    image_url = request.json.get('image_url')
    if not image_url:
        return jsonify({'error': 'Missing image_url'}), 400
        
    try:
        # Detach from session log - delete the image and remove it from history
        success = asyncio.run(runner.delete_image_from_session(session_id, image_url))
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Image file not found in session or disk'}), 404
    except Exception as e:
        print(f"Error deleting image file {image_url} from session {session_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/regenerate_image', methods=['POST'])
@requires_auth
def regenerate_image():
    session_id = request.json.get('session_id', 'default')
    old_image_url = request.json.get('old_image_url')
    prompt = request.json.get('prompt')
    
    if not old_image_url:
        return jsonify({'error': 'Missing old_image_url'}), 400
        
    # Normalize old_image_url to pathname
    if "://" in old_image_url:
        from urllib.parse import urlparse
        old_image_url = urlparse(old_image_url).path

    if not prompt:
        import os
        filename = os.path.basename(old_image_url)
        # 1. Try to find the prompt in the program sidecar JSON file (most reliable and clean)
        try:
            from utils.program import get_active_program
            active_program = get_active_program()
            filename_only = os.path.basename(old_image_url)
            json_path = find_image_sidecar_json(filename_only, active_program)

            if json_path and os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    prompt = meta.get('prompt')
                    if prompt:
                        print(f"[DEBUG REROLL] Found prompt in sidecar JSON: {prompt}")
        except Exception as je:
            print(f"Error reading sidecar JSON: {je}")

        # 2. Try to find the prompt in session history (fallback)
        if not prompt:
            try:
                chat_history = asyncio.run(runner.get_history(session_id))
                for msg in chat_history:
                    tool_calls = msg.get('tool_calls', [])
                    if not tool_calls:
                        continue
                    calls = {}
                    for tc in tool_calls:
                        if tc.get('type') == 'call' and tc.get('name') == 'generate_program_portrait':
                            call_id = tc.get('id')
                            args = tc.get('args', {})
                            p = args.get('prompt')
                            if call_id and p:
                                calls[call_id] = p
                    for tc in tool_calls:
                        if tc.get('type') == 'response' and tc.get('name') == 'generate_program_portrait':
                            call_id = tc.get('id')
                            response_val = tc.get('response', '')
                            if call_id in calls and filename in response_val:
                                prompt = calls[call_id]
                                print(f"[DEBUG REROLL] Found prompt in history matching filename '{filename}': {prompt}")
                                break
                    if prompt:
                        break
            except Exception as he:
                print(f"Error scanning session history for prompt: {he}")

        if not prompt:
            return jsonify({'error': 'Original prompt not found. Unable to regenerate image.'}), 400

    try:
        import tools
        tools.current_session_id.set(session_id)
        with tools.session_tool_calls_lock:
            tools.session_tool_calls[session_id] = []
        use_imagen = request.json.get('use_imagen', False)
        # Generate new portrait
        if use_imagen:
            new_markdown = tools.generate_imagen(prompt)
        else:
            new_markdown = tools.generate_local_image(prompt)
        if new_markdown.startswith("Error"):
            return jsonify({'error': new_markdown}), 500
            
        # Parse the new image URL from Markdown link: ![...](/images/...)
        new_image_url = None
        if new_markdown.startswith("![") and new_markdown.endswith(")"):
            new_image_url = new_markdown.split("(", 1)[1][:-1]
            
        if not new_image_url:
            return jsonify({'error': f'Failed to parse generated image markdown: {new_markdown}'}), 500
            
        # Replace in session history
        success = asyncio.run(runner.replace_image_in_session(session_id, old_image_url, new_image_url, new_prompt=prompt))
        if success:
            return jsonify({
                'status': 'success',
                'new_image_url': new_image_url
            })
        else:
            return jsonify({'error': 'Original image not found in session'}), 404
    except Exception as e:
        print(f"Error regenerating image in session {session_id}: {e}")
        return jsonify({'error': str(e)}), 500

import threading
import uuid

active_generations = {}
active_generations_lock = threading.Lock()

def run_background_video_gen(task_id, session_id, image_url, local_path, prompt):
    import tools
    import asyncio
    
    with active_generations_lock:
        if task_id in active_generations:
            active_generations[task_id]['status'] = 'generating'
            active_generations[task_id]['progress'] = 20
            
    try:
        # Call video generation
        new_video_url = tools.generate_video_from_image(local_path, prompt)
        
        # Replace the image in session history
        success = asyncio.run(runner.replace_image_with_video_in_session(session_id, image_url, new_video_url))
        
        with active_generations_lock:
            if task_id in active_generations:
                active_generations[task_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'result_url': new_video_url,
                    'history_updated': success
                })
                
    except Exception as e:
        print(f"Error in background generation task {task_id}: {e}")
        with active_generations_lock:
            if task_id in active_generations:
                active_generations[task_id].update({
                    'status': 'failed',
                    'progress': 100,
                    'error': str(e)
                })

@app.route('/api/animate_image', methods=['POST'])
@requires_auth
def animate_image():
    session_id = request.json.get('session_id', 'default')
    image_url = request.json.get('image_url')
    prompt = request.json.get('prompt', 'gentle head turn, smiling, blinking, looking at camera')
    
    if not image_url:
        return jsonify({'error': 'Missing image_url'}), 400
        
    try:
        from runner_interface import _get_safe_local_path
        
        # Resolve to safe local path
        local_path = _get_safe_local_path(image_url)
        if not local_path or not os.path.exists(local_path):
            return jsonify({'error': f'Image file not found: {image_url}'}), 404
            
        # Create a unique task ID
        task_id = f"gen_{int(time.time())}_{uuid.uuid4().hex[:4]}"
        
        # Initialize task in queue
        with active_generations_lock:
            active_generations[task_id] = {
                'task_id': task_id,
                'status': 'queued',
                'progress': 0,
                'prompt': prompt,
                'source_image': image_url,
                'session_id': session_id,
                'timestamp': time.time(),
                'result_url': None,
                'error': None
            }
            
        # Spawn background thread
        t = threading.Thread(
            target=run_background_video_gen,
            args=(task_id, session_id, image_url, local_path, prompt),
            daemon=True
        )
        t.start()
        
        return jsonify({
            'status': 'queued',
            'task_id': task_id
        })
            
    except Exception as e:
        print(f"Error starting animation queue for {image_url}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generations', methods=['GET'])
@requires_auth
def list_generations():
    with active_generations_lock:
        tasks = list(active_generations.values())
        tasks.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify({
            'generations': tasks
        })


@app.route('/list_images', methods=['GET'])
@requires_auth
def list_images():
    try:
        active_program = os.getenv("ACTIVE_PROGRAM", "sebile")
        program_dir = os.path.join('core', 'programs', active_program)
        image_urls = []
        
        for subdir, url_prefix in [('portraits', '/images/portraits'), ('media', '/images/media')]:
            scan_dir = os.path.join(program_dir, subdir)
            if not os.path.exists(scan_dir):
                continue
            files = os.listdir(scan_dir)
            media_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.webm')) and f.lower() != 'profile.png']
            for f in media_files:
                mtime = os.path.getmtime(os.path.join(scan_dir, f))
                image_urls.append({'url': f"{url_prefix}/{f}", 'mtime': mtime})
        
        image_urls.sort(key=lambda x: x['mtime'], reverse=True)
        return jsonify({'images': [item['url'] for item in image_urls]})
    except Exception as e:
        print(f"Error listing images: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/pending_tool_call', methods=['GET'])
@requires_auth
def get_pending_tool_call():
    import tools
    pending = None
    for call_id, info in list(tools.pending_tool_calls.items()):
        if info['status'] == 'pending':
            pending = {
                'call_id': call_id,
                'tool_name': info['tool_name'],
                'details': info['details']
            }
            break
    active_list = list(tools.active_running_tools.keys())
    return jsonify({
        'call_id': pending['call_id'] if pending else None,
        'tool_name': pending['tool_name'] if pending else None,
        'details': pending['details'] if pending else None,
        'active_tools': active_list
    })

@app.route('/api/cancel_chat', methods=['POST'])
@requires_auth
def cancel_chat():
    session_id = request.json.get('session_id', 'default')
    from runner_interface import cancelled_sessions
    cancelled_sessions.add(session_id)
    print(f"[CANCEL] Session cancellation requested: {session_id}", flush=True)
    return jsonify({'status': 'success'})

@app.route('/api/session_tool_calls', methods=['GET'])
@requires_auth
def get_session_tool_calls():
    session_id = request.args.get('session_id', 'default')
    import tools
    with tools.session_tool_calls_lock:
        calls = tools.session_tool_calls.get(session_id, [])
        return jsonify({'tool_calls': list(calls)})

@app.route('/approve_tool', methods=['POST'])
@requires_auth
def approve_tool():
    import tools
    call_id = request.json.get('call_id')
    status = request.json.get('status')
    
    if call_id in tools.pending_tool_calls:
        tools.pending_tool_calls[call_id]['status'] = status
        event = tools.pending_tool_calls[call_id].get('event')
        if event:
            event.set()
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Tool call not found'}), 404

from utils.models import fetch_local_models

@app.route('/models', methods=['GET'])
@requires_auth
def get_models():
    # Determine the active runner backend
    runner_backend = os.getenv("RUNNER_BACKEND", "opensource").lower()
    
    # Check if Remote API key and Cloud URL are validly configured
    remote_key = os.getenv("REMOTE_API_KEY")
    remote_cloud_url = os.getenv("REMOTE_CLOUD_URL")
    is_remote_configured = bool(
        remote_key and remote_key.strip() and remote_key != "your_remote_api_key_here" and
        remote_cloud_url and remote_cloud_url.strip() and remote_cloud_url != "your_remote_cloud_url_here"
    )
    
    from utils.local_llm_manager import check_status, check_installed
    is_local_online = check_status()
    
    # 1. Fetch dynamic local models (only actively loaded models in Local LLM server)
    models = fetch_local_models()
    
    # Default fallback: use the first loaded local model if available, otherwise "local-llm"
    default_model = "local-llm"
    if models and models[0]["value"] != "local-llm":
        default_model = models[0]["value"]
        
    temperature = load_temperature()
        
    return jsonify({
        "models": models,
        "default": default_model,
        "status": {
            "remote_configured": is_remote_configured,
            "remote_model": os.getenv("REMOTE_MODEL", "gemini-3.1-flash-lite"),
            "remote_url": remote_cloud_url,
            "local_online": is_local_online,
            "local_installed": check_installed(),
            "temperature": temperature
        }
    })

@app.route('/api/project_settings', methods=['GET', 'POST'])
@requires_auth
def project_settings():
    from variables import VARIABLES_DIR
    import json
    settings_path = os.path.join(VARIABLES_DIR, "project_settings.json")
    
    # Get active program
    from utils.program import get_active_program
    active_prog = get_active_program()
    default_folder = os.path.normpath(os.path.join(os.getcwd(), 'core', 'programs', active_prog))
    
    # Define default settings
    default_settings = {
        "folders": [default_folder],
        "security_preset": "ask_always",
        "artifact_review_policy": "ask_always",
        "search_engine": "web_crawling",
        "searxng_url": "",
        "tts_voice": "af_heart"
    }
    
    if request.method == 'GET':
        if not os.path.exists(settings_path):
            try:
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(default_settings, f, indent=2)
                return jsonify(default_settings)
            except Exception as e:
                print(f"Error creating default project settings: {e}")
                return jsonify(default_settings)
        else:
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                # Ensure fields are present
                dirty = False
                for k, v in default_settings.items():
                    if k not in settings:
                        settings[k] = v
                        dirty = True
                
                # Check if the first folder needs to be updated to the new program
                if "folders" in settings and len(settings["folders"]) > 0:
                    first_folder = os.path.normpath(settings["folders"][0])
                    cwd = os.path.normpath(os.getcwd())
                    is_old_program_dir = ("core" in first_folder and "programs" in first_folder) or first_folder == cwd
                    if is_old_program_dir and first_folder != default_folder:
                        settings["folders"][0] = default_folder
                        dirty = True
                
                if settings.get("search_engine") in ("sovereign_hybrid", "sovereign_search"):
                    settings["search_engine"] = "web_crawling"
                    dirty = True
                if dirty:
                    with open(settings_path, "w", encoding="utf-8") as f:
                        json.dump(settings, f, indent=2)
                return jsonify(settings)
            except Exception as e:
                print(f"Error reading project settings: {e}")
                return jsonify(default_settings)
                
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            folders = data.get("folders", [])
            security_preset = data.get("security_preset", "ask_always")
            artifact_review_policy = data.get("artifact_review_policy", "ask_always")
            search_engine = data.get("search_engine", "web_crawling")
            searxng_url = data.get("searxng_url", "")
            tts_voice = data.get("tts_voice", "af_heart")
            
            cleaned_folders = []
            seen = set()
            
            # Ensure default_folder is always the first folder
            cleaned_folders.append(default_folder)
            seen.add(default_folder.lower() if os.name == 'nt' else default_folder)
            
            for folder in folders:
                if not folder:
                    continue
                norm = os.path.normpath(folder)
                key = norm.lower() if os.name == 'nt' else norm
                if key not in seen:
                    cleaned_folders.append(norm)
                    seen.add(key)
            
            # Load existing settings to preserve other keys (active_program, active_user)
            settings = {}
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r", encoding="utf-8") as f:
                        settings = json.load(f)
                except Exception:
                    pass
            
            settings.update({
                "folders": cleaned_folders,
                "security_preset": security_preset,
                "artifact_review_policy": artifact_review_policy,
                "search_engine": search_engine,
                "searxng_url": searxng_url,
                "tts_voice": tts_voice
            })
            
            # Keep environment variable in sync
            os.environ["TTS_VOICE"] = tts_voice
            
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return jsonify({"status": "success", "settings": settings})
        except Exception as e:
            print(f"Error saving project settings: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/save_generation_params', methods=['POST'])
@requires_auth
def save_generation_params():
    try:
        from variables import VARIABLES_DIR
        settings_path = os.path.join(VARIABLES_DIR, "project_settings.json")
        
        data = request.get_json() or {}
        temperature = data.get("temperature")
        if temperature is None:
            return jsonify({"error": "Missing temperature"}), 400
            
        try:
            temperature = float(temperature)
        except ValueError:
            return jsonify({"error": "Invalid temperature value"}), 400
            
        settings = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception:
                pass
                
        settings["temperature"] = temperature
        
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            
        # Re-initialize runner to apply the configuration dynamically
        init_runner()
        
        return jsonify({"status": "success", "settings": settings})
    except Exception as e:
        print(f"Error saving generation params: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/save_config', methods=['POST'])
@requires_auth
def save_config():
    try:
        data = request.get_json() or {}
        remote_api_key = data.get('remote_api_key', data.get('gemini_api_key', '')).strip()
        remote_cloud_url = data.get('remote_cloud_url', data.get('project_id', '')).strip()
        remote_model = data.get('remote_model', data.get('gemini_model', '')).strip()
        
        existing_key = os.getenv("REMOTE_API_KEY")
        
        target_key = remote_api_key or existing_key
        
        if not target_key:
            return jsonify({'error': 'Remote API Key must be provided.'}), 400
            
        env_path = os.path.join(base_dir, '.env')
        
        # Read env lines
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []
            
        updated_key = False
        updated_url = False
        updated_model = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('REMOTE_API_KEY=') and remote_api_key:
                lines[i] = f"REMOTE_API_KEY={remote_api_key}\n"
                updated_key = True
            elif stripped.startswith('REMOTE_CLOUD_URL=') and remote_cloud_url:
                lines[i] = f"REMOTE_CLOUD_URL={remote_cloud_url}\n"
                updated_url = True
            elif stripped.startswith('REMOTE_MODEL=') and remote_model:
                lines[i] = f"REMOTE_MODEL={remote_model}\n"
                updated_model = True
                
        if remote_api_key:
            if not updated_key:
                lines.append(f"REMOTE_API_KEY={remote_api_key}\n")
            os.environ["REMOTE_API_KEY"] = remote_api_key
        if remote_cloud_url:
            if not updated_url:
                lines.append(f"REMOTE_CLOUD_URL={remote_cloud_url}\n")
            os.environ["REMOTE_CLOUD_URL"] = remote_cloud_url
        if remote_model:
            if not updated_model:
                lines.append(f"REMOTE_MODEL={remote_model}\n")
            os.environ["REMOTE_MODEL"] = remote_model
            
        # Re-initialize the runner backend dynamically
        init_runner()
        
        # Clear runner sessions history to reload character instructions
        runner.sessions_history.clear()
                
        # Clean up legacy GCP/Project ID lines to avoid bloat
        lines = [l for l in lines if not l.strip().startswith('PROJECT_ID=')]
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        print(">>> Dynamic setup complete: Saved configuration credentials successfully!")
        return jsonify({'status': 'success', 'message': 'Configuration credentials saved successfully!'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/speech_cache/<path:filename>')
@requires_auth
def serve_speech_cache(filename):
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "skills", "speech_generation", "speech_cache")
    return send_from_directory(cache_dir, filename)

@app.route('/api/tts', methods=['POST'])
@requires_auth
def api_tts():
    try:
        data = request.get_json() or {}
        message_id = data.get('message_id')
        text = data.get('text')
        
        if not message_id or not text:
            return jsonify({'error': 'Missing message_id or text'}), 400
            
        from core.program_config import replace_placeholders
        text = replace_placeholders(text)
        
        from core.skills.speech_generation.speech import SpeechManager
        manager = SpeechManager()
        audio_url = manager.get_speech_file(text, message_id)
        if audio_url:
            return jsonify({'success': True, 'audio_url': audio_url})
        else:
            return jsonify({'success': False, 'error': 'Speech generation failed'}), 500
    except Exception as e:
        print(f"Error in /api/tts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/voice_call/start', methods=['POST'])
@requires_auth
def start_voice_call_api():
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id', 'default')
        voice_session_id = f"{session_id}_voice"
        
        # 1. Reset/Clear any existing voice session
        asyncio.run(runner.reset_session(voice_session_id))
        
        # 2. Clone context from main session to voice session
        asyncio.run(runner.clone_history(session_id, voice_session_id, []))
        
        print(f"[VOICE CALL] Initialized voice session: {voice_session_id} cloned from {session_id}")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in /api/voice_call/start: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/voice_call/save', methods=['POST'])
@requires_auth
def save_voice_call():
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id', 'default')
        transcript = data.get('transcript')
        voice_session_id = f"{session_id}_voice"
        
        if not transcript:
            return jsonify({'error': 'Missing transcript'}), 400
            
        # 1. Save consolidated transcript message to main session history
        success = asyncio.run(runner.append_voice_call(session_id, transcript))
        
        # 2. Reset/Clean up temporary voice session from memory/disk
        asyncio.run(runner.reset_session(voice_session_id))
        
        print(f"[VOICE CALL] Saved transcript to main session {session_id} and cleared temporary voice session {voice_session_id}")
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to append voice call to session'}), 500
    except Exception as e:
        print(f"Error in /api/voice_call/save: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- VECTORIZED DATA BANK API ENDPOINTS ---
from core.skills.vectorized_databank.databank import DataBankManager

@app.route('/api/databank/files', methods=['GET'])
@requires_auth
def databank_list_files():
    try:
        from utils.program import get_active_program
        prog_id = request.args.get('program_id') or get_active_program()
        manager = DataBankManager(program_id=prog_id)
        files = manager.list_documents()
        return jsonify({"files": files})
    except Exception as e:
        print(f"Error listing databank files: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/databank/upload', methods=['POST'])
@requires_auth
def databank_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
        
    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    temp_path = None
    try:
        from utils.program import get_active_program
        prog_id = request.form.get('program_id') or get_active_program()
        # Create temp folder inside workspace for uploads
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Sanitize filename
        from werkzeug.utils import secure_filename
        filename = secure_filename(uploaded_file.filename)
        temp_path = os.path.join(temp_dir, filename)
        uploaded_file.save(temp_path)
        
        manager = DataBankManager(program_id=prog_id)
        doc_id = manager.ingest_file(temp_path, uploaded_file.filename)
        return jsonify({"status": "success", "id": doc_id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error uploading to databank: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as re:
                print(f"Error cleaning up temporary file {temp_path}: {re}")

@app.route('/api/databank/scrape', methods=['POST'])
@requires_auth
def databank_scrape():
    req_json = request.get_json(silent=True) or {}
    url = req_json.get('url')
    if not url:
        return jsonify({"error": "Missing URL"}), 400
        
    try:
        from utils.program import get_active_program
        prog_id = req_json.get('program_id') or get_active_program()
        manager = DataBankManager(program_id=prog_id)
        doc_id = manager.ingest_url(url)
        return jsonify({"status": "success", "id": doc_id})
    except Exception as e:
        print(f"Error scraping url: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/databank/delete', methods=['POST'])
@requires_auth
def databank_delete():
    req_json = request.get_json(silent=True) or {}
    doc_id = req_json.get('id')
    if not doc_id:
        return jsonify({"error": "Missing document ID"}), 400
        
    try:
        from utils.program import get_active_program
        prog_id = req_json.get('program_id') or get_active_program()
        manager = DataBankManager(program_id=prog_id)
        success = manager.delete_document(doc_id)
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "Document not found"}), 404
    except Exception as e:
        print(f"Error deleting document {doc_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/databank/purge', methods=['POST'])
@requires_auth
def databank_purge():
    try:
        from utils.program import get_active_program
        req_json = request.get_json(silent=True) or {}
        prog_id = req_json.get('program_id') or request.args.get('program_id') or get_active_program()
        manager = DataBankManager(program_id=prog_id)
        manager.purge_all()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error purging databank: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# Lorebook routes
# ---------------------------------------------------------------------------

@app.route('/api/lorebooks', methods=['GET'])
@requires_auth
def list_lorebooks_route():
    try:
        from utils.program import get_active_program
        from utils.lorebook import list_lorebooks
        from variables import PROGRAMS_DIR
        program_id = get_active_program()
        books = list_lorebooks(program_id, PROGRAMS_DIR)
        for b in books:
            b['program_id'] = program_id
        return jsonify({'lorebooks': books, 'program_id': program_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lorebooks/import', methods=['POST'])
@requires_auth
def import_lorebook_route():
    try:
        from utils.program import get_active_program
        from utils.lorebook import import_lorebook
        from variables import PROGRAMS_DIR
        program_id = get_active_program()
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        f = request.files['file']
        if not f.filename or not f.filename.endswith('.json'):
            return jsonify({'error': 'Only .json lorebook files are accepted'}), 400
        book_data = json.loads(f.read().decode('utf-8'))
        dest = import_lorebook(program_id, book_data, f.filename, PROGRAMS_DIR)
        return jsonify({'success': True, 'path': dest})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def find_lorebook_path(filename, program_id):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    global_lore_dir = os.path.join(base_dir, "core", "lorebooks")
    
    # 1. Search in global core/lorebooks/
    if os.path.isdir(global_lore_dir):
        for root, _, files in os.walk(global_lore_dir):
            if filename in files:
                return os.path.join(root, filename)
                
    # 2. Search in program-specific lorebooks
    from variables import PROGRAMS_DIR
    prog_lore_dir = os.path.join(PROGRAMS_DIR, program_id, 'lorebooks')
    fpath = os.path.join(prog_lore_dir, filename)
    if os.path.exists(fpath):
        return fpath
        
    return None


@app.route('/api/lorebooks/<filename>/export', methods=['GET'])
@requires_auth
def export_lorebook_route(filename):
    try:
        from utils.program import get_active_program
        program_id = get_active_program()
        fpath = find_lorebook_path(filename, program_id)
        if not fpath or not os.path.exists(fpath):
            return jsonify({'error': 'Lorebook not found'}), 404
        with open(fpath, encoding='utf-8') as lf:
            book_data = json.load(lf)
        resp = make_response(json.dumps(book_data, indent=2, ensure_ascii=False))
        resp.headers['Content-Type'] = 'application/json'
        resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lorebooks/<filename>/delete', methods=['POST'])
@requires_auth
def delete_lorebook_route(filename):
    try:
        from utils.program import get_active_program
        from utils.lorebook import delete_lorebook
        from variables import PROGRAMS_DIR
        program_id = get_active_program()
        deleted = delete_lorebook(program_id, filename, PROGRAMS_DIR)
        return jsonify({'success': deleted})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lorebooks/card/entries', methods=['GET'])
@requires_auth
def get_card_lorebook_entries():
    """Return entries from the embedded character_book in the active program card."""
    try:
        from utils.program import get_active_program
        from variables import PROGRAMS_DIR
        program_id = get_active_program()
        card_path = os.path.join(PROGRAMS_DIR, program_id, f'{program_id}.json')
        if not os.path.exists(card_path):
            return jsonify({'error': 'Card not found'}), 404
        with open(card_path, encoding='utf-8') as f:
            card = json.load(f)
        cb = card.get('data', card).get('character_book', {})
        entries = cb.get('entries', [])
        if isinstance(entries, dict):
            entries = list(entries.values())
        return jsonify({'name': cb.get('name', program_id), 'entries': entries})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lorebooks/card/save', methods=['POST'])
@requires_auth
def save_card_lorebook_entries():
    """Write updated entries back into character_book in the active program card."""
    try:
        from utils.program import get_active_program
        from variables import PROGRAMS_DIR
        program_id = get_active_program()
        card_path = os.path.join(PROGRAMS_DIR, program_id, f'{program_id}.json')
        if not os.path.exists(card_path):
            return jsonify({'error': 'Card not found'}), 404
        data = request.get_json(silent=True) or {}
        with open(card_path, encoding='utf-8') as f:
            card = json.load(f)
        # Navigate to character_book regardless of v2/v3 wrapping
        data_block = card.get('data', card)
        if 'character_book' not in data_block:
            data_block['character_book'] = {'name': program_id, 'entries': []}
        if 'entries' in data:
            data_block['character_book']['entries'] = data['entries']
        with open(card_path, 'w', encoding='utf-8') as f:
            json.dump(card, f, indent=2, ensure_ascii=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lorebooks/<filename>/entries', methods=['GET'])
@requires_auth
def get_lorebook_entries(filename):
    """Return the raw entry list for a lorebook file so the UI can render an editor."""
    try:
        from utils.program import get_active_program
        program_id = get_active_program()
        fpath = find_lorebook_path(filename, program_id)
        if not fpath or not os.path.exists(fpath):
            return jsonify({'error': 'Lorebook not found'}), 404
        with open(fpath, encoding='utf-8') as lf:
            book = json.load(lf)
        # Normalise entries to list form
        entries = book.get('entries', [])
        if isinstance(entries, dict):
            entries = list(entries.values())
        return jsonify({'name': book.get('name', filename), 'entries': entries})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lorebooks/<filename>/save', methods=['POST'])
@requires_auth
def save_lorebook_entries(filename):
    """Overwrite a lorebook file with updated entries from the editor."""
    try:
        from utils.program import get_active_program
        program_id = get_active_program()
        fpath = find_lorebook_path(filename, program_id)
        if not fpath or not os.path.exists(fpath):
            return jsonify({'error': 'Lorebook not found'}), 404
        data = request.get_json(silent=True) or {}
        with open(fpath, encoding='utf-8') as lf:
            book = json.load(lf)
        if 'entries' in data:
            # Store as list (v3 format)
            book['entries'] = data['entries']
        if 'name' in data:
            book['name'] = data['name']
        with open(fpath, 'w', encoding='utf-8') as lf:
            json.dump(book, lf, indent=2, ensure_ascii=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/memories', methods=['GET'])
@requires_auth
def get_program_memories():
    try:
        manager = DataBankManager()
        memories = manager.get_all_memories()
        return jsonify({"memories": memories})
    except Exception as e:
        print(f"Error loading program memories: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/programs/memories/delete', methods=['POST'])
@requires_auth
def delete_memory():
    data = request.json or {}
    session_id = data.get("session_id", "default")
    timestamp = data.get("timestamp")
    if timestamp is None:
        return jsonify({"error": "Missing timestamp"}), 400
    try:
        timestamp = float(timestamp)
    except ValueError:
        return jsonify({"error": "Invalid timestamp"}), 400
    try:
        success = asyncio.run(runner.delete_system_memory(session_id, timestamp))
        return jsonify({"status": "success", "deleted": success})
    except Exception as e:
        print(f"Error deleting memory for session {session_id} at {timestamp}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/quests', methods=['GET'])
@requires_auth
def list_quests():
    try:
        from utils.program import get_active_program, get_active_user
        from engine.quest_tracker import load_quest_stages, get_current_stage, get_quest_display_data, sync_quest_stage_with_location

        user = get_active_user()
        world_state = sync_quest_stage_with_location(user)
        current_stage_num = world_state.get("quest_stage", 10)
        stages = load_quest_stages()

        # 1 & 2. Main Quests (Active Quest with granular checkboxes & Archived Completed Quests)
        quests, completed_quests = get_quest_display_data(current_stage_num, stages)
        
        # Inject location into active main quest
        for q in quests:
            if q.get("is_main_quest"):
                q["location"] = f"{world_state.get('current_location', 'Imperial Dungeon')}, {world_state.get('current_province', 'Cyrodiil')}"

        # 3 & 4. Companion / Local Side Quests (Active & Archived)
        from engine.side_quests import get_side_quest_display_data
        side_active, side_archived = get_side_quest_display_data()
        quests.extend(side_active)
        completed_quests.extend(side_archived)
                
        return jsonify({
            "quests": quests,
            "completed_quests": completed_quests,
            "quest_stage": current_stage_num
        })
    except Exception as e:
        print(f"Error loading quests: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/quests/<quest_id>/delete', methods=['POST'])
@requires_auth
def delete_quest(quest_id):
    try:
        from utils.program import get_active_program
        active_program = get_active_program()
        quests_path = os.path.join('core', 'programs', active_program, 'quest_log.json')
        
        if os.path.exists(quests_path):
            with open(quests_path, 'r', encoding='utf-8') as f:
                quests = json.load(f)
            quests = [q for q in quests if q['id'] != quest_id]
            with open(quests_path, 'w', encoding='utf-8') as f:
                json.dump(quests, f, indent=2, ensure_ascii=False)
                
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error deleting quest {quest_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/quests/<quest_id>/abandon', methods=['POST'])
@requires_auth
def abandon_quest(quest_id):
    try:
        from utils.program import get_active_program
        active_program = get_active_program()
        program_dir = os.path.join('core', 'programs', active_program)
        quests_path = os.path.join(program_dir, 'quest_log.json')
        history_path = os.path.join(program_dir, 'quest_history.json')
        quest_data = None
        
        if os.path.exists(quests_path):
            with open(quests_path, 'r', encoding='utf-8') as f:
                quests = json.load(f)
            quest_data = next((q for q in quests if q.get('id') == quest_id), None)
            if quest_data:
                quests = [q for q in quests if q.get('id') != quest_id]
                with open(quests_path, 'w', encoding='utf-8') as f:
                    json.dump(quests, f, indent=2, ensure_ascii=False)
        
        if not quest_data:
            return jsonify({"error": "Quest not found"}), 404

        # Archive as failed in quest_history.json
        quest_data["status"] = "failed"
        history = []
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                if not isinstance(history, list):
                    history = []
            except Exception:
                history = []
        history.append(quest_data)
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
            
        session_id = 'default'
        if request.is_json:
            session_id = request.json.get('session_id', 'default')
            
        title = quest_data.get("title", "")
        system_message = f"[SYSTEM: Player has abandoned and failed the side quest: \"{title}\"]"
        
        asyncio.run(runner.append_message_to_session(session_id, "user", system_message))
        
        return jsonify({
            "status": "success",
            "title": title
        })
    except Exception as e:
        print(f"Error abandoning quest {quest_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/quests/<quest_id>/download', methods=['GET'])
@requires_auth
def download_quest(quest_id):
    try:
        from utils.program import get_active_program
        active_program = get_active_program()
        quests_path = os.path.join('core', 'programs', active_program, 'quest_log.json')
        if not os.path.exists(quests_path):
            return jsonify({"error": "No quests found"}), 404
        with open(quests_path, 'r', encoding='utf-8') as f:
            quests = json.load(f)
        quest = next((q for q in quests if q['id'] == quest_id), None)
        if not quest:
            return jsonify({"error": "Quest not found"}), 404

        title = quest.get('title', 'Quest')
        location = quest.get('location', '')
        objectives = quest.get('objectives', [])
        notes = "\n".join(objectives)
        due_str = quest.get('due', '')

        # Parse start time
        try:
            from datetime import datetime, timedelta, timezone
            dt_start = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
        except Exception:
            dt_start = datetime.now(timezone.utc)
            
        dt_end = dt_start + timedelta(hours=1)
        
        stamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        start_str = dt_start.strftime("%Y%m%dT%H%M%SZ")
        end_str = dt_end.strftime("%Y%m%dT%H%M%SZ")
        
        clean_desc = notes.replace("\n", "\\n")
        
        try:
            trigger_minutes = int(quest.get('reminder_minutes', 15))
        except (ValueError, TypeError):
            trigger_minutes = 15

        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//The Arena//Quest Giver//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{quest_id}@thearena
DTSTAMP:{stamp_str}
DTSTART:{start_str}
DTEND:{end_str}
SUMMARY:{title}
DESCRIPTION:{clean_desc}
LOCATION:{location}
BEGIN:VALARM
TRIGGER:-PT{trigger_minutes}M
ACTION:DISPLAY
DESCRIPTION:Reminder: {title} is due soon!
END:VALARM
END:VEVENT
END:VCALENDAR"""

        return Response(
            ics_content.strip(),
            mimetype="text/calendar",
            headers={"Content-Disposition": f"attachment; filename=\"{quest_id}.ics\""}
        )
    except Exception as e:
        print(f"Error downloading quest {quest_id}: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/sessions', methods=['GET'])
@requires_auth
def list_sessions():
    try:
        active_program = os.environ.get("ACTIVE_PROGRAM", "sebile")
        sessions_dir = os.path.join(base_dir, "core", "programs", active_program, "sessions")
        
        sessions = []
        if os.path.exists(sessions_dir):
            for file in os.listdir(sessions_dir):
                if file.endswith('.json') and not file.endswith('_voice.json'):
                    session_name = file[:-5]
                    sessions.append(session_name)
        
        # Ensure 'default' is always in the list
        if 'default' not in sessions:
            sessions.insert(0, 'default')
        else:
            sessions.remove('default')
            sessions.insert(0, 'default')
            
        return jsonify({
            'status': 'success',
            'sessions': sessions
        })
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/programs', methods=['GET'])
@requires_auth
def list_programs():
    try:
        active_program = os.getenv("ACTIVE_PROGRAM", "sebile")
        from variables import PROGRAMS_DIR
        programs_dir = PROGRAMS_DIR
        
        programs = []
        if os.path.exists(programs_dir):
            for folder in os.listdir(programs_dir):
                folder_path = os.path.join(programs_dir, folder)
                if os.path.isdir(folder_path):
                    program_name = folder.title()
                    json_path = os.path.join(folder_path, f"{folder}.json")
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, "r", encoding="utf-8") as jf:
                                jdata = json.load(jf)
                                # Unwrap v3 data block
                                card = jdata.get("data", jdata)
                                if card.get("name"):
                                    program_name = card["name"]
                        except Exception:
                            pass
                    else:
                        for file in os.listdir(folder_path):
                            if file.lower().endswith('.md') and not file.lower().startswith('user'):
                                program_name = os.path.splitext(file)[0].title()
                                break
                    # Read theme color from theme.json
                    theme_color = "#38bdf8"
                    tdata = load_theme(folder)
                    if tdata:
                        theme_color = tdata.get("primary_accent") or tdata.get("main_color") or theme_color
                            
                    # Check if portraits/profile.png exists
                    has_profile = False
                    profile_path = os.path.join(folder_path, "portraits", "profile.png")
                    if os.path.exists(profile_path):
                        has_profile = True
                        
                    # Read recruited flag from card extensions
                    recruited = False
                    json_path2 = os.path.join(folder_path, f"{folder}.json")
                    if os.path.exists(json_path2):
                        try:
                            with open(json_path2, "r", encoding="utf-8") as jf2:
                                jdata2 = json.load(jf2)
                                card2 = jdata2.get("data", jdata2)
                                exts2 = card2.get("extensions", {})
                                san2 = exts2.get("arena", exts2.get("sanctuary", {}))
                                # ria_silmane is always recruited (spectral guide, always present)
                                if folder == "ria_silmane":
                                    recruited = True
                                else:
                                    recruited = bool(san2.get("recruited", False))
                        except Exception:
                            recruited = folder == "ria_silmane"
                    else:
                        recruited = folder == "ria_silmane"

                    programs.append({
                        'id': folder,
                        'name': program_name,
                        'active': folder == active_program,
                        'theme_color': theme_color,
                        'has_profile': has_profile,
                        'recruited': recruited
                    })
        return jsonify({'programs': programs, 'active': active_program})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/programs/select', methods=['POST'])
@requires_auth
def select_program():
    try:
        data = request.get_json(silent=True) or {}
        program_id = data.get('program_id')
        if not program_id:
            return jsonify({'error': 'Missing program_id'}), 400
            
        program_path = os.path.join(base_dir, 'core', 'programs', program_id)
        if not os.path.exists(program_path):
            return jsonify({'error': f"Program '{program_id}' does not exist"}), 404
            
        # Update environment variable
        os.environ["ACTIVE_PROGRAM"] = program_id
        
        # Update active program settings
        try:
            from utils.program import set_active_program
            set_active_program(program_id)
        except Exception as e:
            print(f"Error persisting ACTIVE_PROGRAM: {e}")
        

        reload_program_state()
            
        theme = load_theme(program_id)

        has_profile = False
        profile_path = os.path.join(program_path, "portraits", "profile.png")
        if os.path.exists(profile_path):
            has_profile = True

        from core.program_config import program_name
        return jsonify({
            'status': 'success',
            'active': program_id,
            'character_name': program_name,
            'theme': theme,
            'has_profile': has_profile
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            with open('server_error.log', 'w', encoding='utf-8') as lf:
                traceback.print_exc(file=lf)
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/palette', methods=['POST'])
@requires_auth
def update_program_palette():
    try:
        data = request.get_json(silent=True) or {}
        program_id = data.get('program_id')
        color = data.get('color')
        
        if not program_id:
            return jsonify({'error': 'Missing program_id'}), 400
        if not color:
            return jsonify({'error': 'Missing color'}), 400
            
        # Validate hex color
        if not re.match(r'^#[0-9a-fA-F]{6}$', color):
            return jsonify({'error': 'Invalid hex color format. Must be #RRGGBB'}), 400
            
        program_path = os.path.join(base_dir, 'core', 'programs', program_id)
        if not os.path.exists(program_path):
            return jsonify({'error': f"Program '{program_id}' does not exist"}), 404
            
        # Regenerate theme.json
        theme_data = generate_character_theme(color)
        theme_path = os.path.join(program_path, "theme.json")
        with open(theme_path, "w", encoding="utf-8") as tf:
            json.dump(theme_data, tf, indent=2, ensure_ascii=False)
            
        return jsonify({
            'status': 'success',
            'program_id': program_id,
            'color': color,
            'theme': theme_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/delete', methods=['POST'])
@requires_auth
def delete_program():
    try:
        data = request.get_json(silent=True) or {}
        program_id = data.get('program_id')
        if not program_id:
            return jsonify({'error': 'Missing program_id'}), 400
            
        if program_id == 'sebile':
            return jsonify({'error': 'Cannot delete default program Sebile'}), 400
            
        program_path = os.path.join(base_dir, 'core', 'programs', program_id)
        if not os.path.exists(program_path):
            return jsonify({'error': f"Program '{program_id}' does not exist"}), 404
            
        # If the deleted program is currently active, switch to Sebile first
        from utils.program import get_active_program, set_active_program
        active_program = get_active_program()
        is_active = (program_id == active_program)
        if is_active:
            os.environ["ACTIVE_PROGRAM"] = "sebile"
            try:
                set_active_program("sebile")
            except Exception as e:
                print(f"Error resetting active program to sebile: {e}")
                
            # Reload program config and re-initialize the runner
            reload_program_state()
                 
        # Delete the program folder recursively
        shutil.rmtree(program_path)
        
        return jsonify({'status': 'success', 'switched_to': 'sebile' if is_active else None})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/rename', methods=['POST'])
@requires_auth
def rename_program():
    try:
        data = request.get_json(silent=True) or {}
        program_id = data.get('program_id')
        new_name = data.get('new_name', '').strip()
        
        if not program_id or not new_name:
            return jsonify({'error': 'Missing program_id or new_name'}), 400
            
        if not re.match(r'^[a-zA-Z0-9_\-]+$', program_id):
            return jsonify({'error': 'Invalid program_id'}), 400
            
        new_id = re.sub(r'[^a-zA-Z0-9_]', '', new_name).lower()
        if not new_id:
            return jsonify({'error': 'Invalid new name (must contain letters, numbers, or underscores)'}), 400
            
        from variables import PROGRAMS_DIR
        old_path = os.path.normpath(os.path.join(PROGRAMS_DIR, program_id))
        new_path = os.path.normpath(os.path.join(PROGRAMS_DIR, new_id))
        
        if not os.path.exists(old_path):
            return jsonify({'error': f"Program '{program_id}' does not exist"}), 404
            
        # If the program is sebile, we keep the folder/id as 'sebile' but update the name in sebile.json
        if program_id == 'sebile':
            json_path = os.path.join(old_path, "sebile.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        jdata = json.load(f)
                    jdata["name"] = new_name
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(jdata, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Error updating Sebile JSON: {e}")
            
            # Reload configuration
            reload_program_state()
            
            active_program = os.getenv("ACTIVE_PROGRAM", "sebile")
            return jsonify({
                'status': 'success',
                'new_id': 'sebile',
                'was_active': (active_program == 'sebile')
            })
            
        # If new_id is different from program_id, perform folder rename
        if new_id != program_id:
            if os.path.exists(new_path):
                return jsonify({'error': f"A program folder named '{new_id}' already exists"}), 400
                
            # Perform directory rename
            shutil.move(old_path, new_path)
            
            # Inside the new directory, rename the json file: old_id.json -> new_id.json
            old_json = os.path.join(new_path, f"{program_id}.json")
            new_json = os.path.join(new_path, f"{new_id}.json")
            if os.path.exists(old_json):
                shutil.move(old_json, new_json)
                
            # Also update fields inside the json file
            if os.path.exists(new_json):
                try:
                    with open(new_json, "r", encoding="utf-8") as f:
                        jdata = json.load(f)
                    data_block = jdata.get("data", jdata)
                    data_block["name"] = new_name
                    exts = data_block.setdefault("extensions", {})
                    arena = exts.setdefault("arena", {})
                    arena["program_id"] = new_id
                    if "character_book" in data_block and isinstance(data_block["character_book"], dict):
                        data_block["character_book"]["name"] = new_name
                    with open(new_json, "w", encoding="utf-8") as f:
                        json.dump(jdata, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Error updating JSON after rename: {e}")
                    
            # Check if active program
            active_program = os.getenv("ACTIVE_PROGRAM", "sebile")
            was_active = (program_id == active_program)
            
            # Update settings (active_program, folders, program_voices)
            from utils.program import _load_settings, _save_settings
            settings = _load_settings()
            
            if was_active:
                os.environ["ACTIVE_PROGRAM"] = new_id
                settings["active_program"] = new_id
                settings["folders"] = [new_path]
                
            if "program_voices" in settings:
                if program_id in settings["program_voices"]:
                    settings["program_voices"][new_id] = settings["program_voices"].pop(program_id)
                    
            _save_settings(settings)
            
            # Reload configuration
            reload_program_state()
            
            return jsonify({
                'status': 'success',
                'new_id': new_id,
                'was_active': was_active
            })
        else:
            # ID is the same, no directory rename needed
            json_path = os.path.join(old_path, f"{program_id}.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        jdata = json.load(f)
                    data_block = jdata.get("data", jdata)
                    data_block["name"] = new_name
                    if "character_book" in data_block and isinstance(data_block["character_book"], dict):
                        data_block["character_book"]["name"] = new_name
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(jdata, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Error updating JSON name: {e}")
                    
            active_program = os.getenv("ACTIVE_PROGRAM", "sebile")
            return jsonify({
                'status': 'success',
                'new_id': program_id,
                'was_active': (program_id == active_program)
            })
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/profile', methods=['GET'])
@requires_auth
def get_program_profile():
    try:
        from utils.program import get_active_program, _load_settings
        from variables import PROGRAMS_DIR
        import json

        program_id = request.args.get('program_id') or get_active_program()
        json_path = os.path.normpath(os.path.join(PROGRAMS_DIR, program_id, f"{program_id}.json"))

        card_data = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                card_data = raw.get('data', raw)
            except Exception:
                pass

        # Inject tts_voice from project settings (stored separately)
        settings = _load_settings()
        program_voices = settings.get('program_voices', {})
        card_data['tts_voice'] = program_voices.get(program_id, settings.get('tts_voice', 'af_heart'))

        return jsonify(card_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/programs/profile/save', methods=['POST'])
@requires_auth
def save_program_profile():
    try:
        from utils.program import get_active_program, set_tts_voice_for_program, _load_settings, _save_settings
        from variables import PROGRAMS_DIR
        import json

        incoming = request.get_json(silent=True) or {}
        program_id = incoming.get('program_id') or get_active_program()
        json_path = os.path.normpath(os.path.join(PROGRAMS_DIR, program_id, f"{program_id}.json"))

        # Extract sidecars before writing card
        tts_voice = incoming.pop('tts_voice', None)
        incoming.pop('program_id', None)

        if tts_voice:
            set_tts_voice_for_program(program_id, tts_voice)

        # Load existing card to preserve spec envelope and any fields not sent by UI
        existing = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception:
                pass

        # Merge incoming data block into existing card
        if existing.get('spec') == 'chara_card_v3' and 'data' in existing:
            existing['data'].update(incoming)
            card_to_write = existing
        else:
            card_to_write = {
                'spec': 'chara_card_v3',
                'spec_version': '3.0',
                'data': incoming
            }

        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(card_to_write, f, indent=2, ensure_ascii=False)

        reload_program_state()
        return jsonify({'status': 'success'})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500



@app.route('/api/programs/journals', methods=['GET'])
@requires_auth
def get_program_journals():
    try:
        from utils.program import get_active_program
        from utils.journals import get_journal_entries
        
        program_id = request.args.get('program_id') or get_active_program()
        entries = get_journal_entries(program_id)
        return jsonify({'journals': entries})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/journals/save', methods=['POST'])
@requires_auth
def save_program_journals():
    try:
        from utils.program import get_active_program
        from utils.journals import get_journal_entries, save_journal_entries, add_journal_entry
        
        data = request.get_json(silent=True) or {}
        entry_id = data.get('id')
        keyphrases_str = data.get('keyphrases', '')
        content = data.get('content', '')
        program_id = data.get('program_id') or get_active_program()
        
        if entry_id:
            entries = get_journal_entries(program_id)
            found = False
            for entry in entries:
                if entry.get("id") == entry_id:
                    entry["keyphrases"] = [k.strip().lower() for k in keyphrases_str.split(",") if k.strip()]
                    entry["content"] = content.strip()[:300]
                    found = True
                    break
            if found:
                save_journal_entries(entries, program_id)
                return jsonify({'status': 'success'})
            else:
                return jsonify({'error': 'Journal entry not found'}), 404
        else:
            add_journal_entry(keyphrases_str, content, program_id)
            return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/journals/delete', methods=['POST'])
@requires_auth
def delete_program_journals():
    try:
        from utils.program import get_active_program
        from utils.journals import delete_journal_entry
        
        data = request.get_json(silent=True) or {}
        entry_id = data.get('id')
        program_id = data.get('program_id') or get_active_program()
        
        if not entry_id:
            return jsonify({'error': 'Missing entry id'}), 400
            
        success = delete_journal_entry(entry_id, program_id)
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to delete or entry not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/character/status', methods=['GET'])
@requires_auth
def get_character_status():
    try:
        from utils.program import get_active_user
        from engine.save_manager import get_active_save_id
        from engine.character import load_character
        from engine.world_engine import load_world_state
        from engine.mechanics import get_modifier
        
        active_user = get_active_user()
        save_id = get_active_save_id()
        character_sheet = load_character(save_id)
        world_state = load_world_state(save_id)
        
        # Calculate d20 modifiers for attributes for convenient UI rendering
        modifiers = {}
        for attr, val in character_sheet.get("attributes", {}).items():
            mod = get_modifier(val)
            modifiers[attr] = f"+{mod}" if mod >= 0 else f"{mod}"
            
        return jsonify({
            "status": "success",
            "active_user": active_user,
            "active_save_id": save_id,
            "character": character_sheet,
            "modifiers": modifiers,
            "world": world_state
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/character/update', methods=['POST'])
@requires_auth
def update_character_profile():
    try:
        data = request.get_json(silent=True) or {}
        from engine.save_manager import get_active_save_id, sync_save_meta
        from engine.character import load_character, save_character, update_character_identity
        
        save_id = get_active_save_id()
        sheet = load_character(save_id)
        
        new_name = data.get("name")
        sheet = update_character_identity(
            sheet=sheet,
            name=new_name,
            race=data.get("race"),
            gender=data.get("gender"),
            character_class=data.get("class"),
            custom_attributes=data.get("attributes")
        )
        save_character(save_id, sheet)
        sync_save_meta(save_id)
        
        if new_name:
            from engine.save_manager import read_save, write_save
            bundle = read_save(save_id)
            profile_text = bundle.get("profile", "")
            lines = profile_text.splitlines()
            if lines and lines[0].startswith("#"):
                lines[0] = f"# {new_name.upper()}"
                bundle["profile"] = "\n".join(lines)
                write_save(save_id, bundle)
        
        return jsonify({
            "status": "success",
            "character": sheet
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/world/provinces', methods=['GET'])
@requires_auth
def get_world_provinces():
    try:
        from pathlib import Path
        prov_path = Path(__file__).parent / "core" / "world" / "provinces.json"
        if prov_path.exists():
            with open(prov_path, "r", encoding="utf-8") as f:
                provinces = json.load(f)
            return jsonify({"status": "success", "provinces": provinces})
        return jsonify({"status": "success", "provinces": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Save State Management Endpoints ──────────────────────────────────────────

@app.route('/api/saves', methods=['GET'])
@requires_auth
def get_saves():
    try:
        from engine.save_manager import list_saves, get_active_save_id
        saves = list_saves()
        active_id = get_active_save_id()
        return jsonify({
            "status": "success",
            "saves": saves,
            "active_save_id": active_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/saves/save', methods=['POST'])
@requires_auth
def save_active_game():
    try:
        from engine.save_manager import save_game
        meta = save_game()
        if hasattr(runner, 'sessions_history'):
            runner.sessions_history.clear()
        reload_program_state()
        return jsonify({
            "status": "success",
            "save": meta
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/saves/new', methods=['POST'])
@requires_auth
def create_new_save():
    try:
        data = request.get_json(silent=True) or {}
        from engine.save_manager import create_save
        meta = create_save(
            name=data.get("name"),
            character_name=data.get("character_name", "Eternal Champion"),
            race=data.get("race", "Nord"),
            gender=data.get("gender", "Male"),
            character_class=data.get("class", "Mage")
        )
        if hasattr(runner, 'sessions_history'):
            runner.sessions_history.clear()
        reload_program_state()
        return jsonify({
            "status": "success",
            "save": meta
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/saves/load', methods=['POST'])
@requires_auth
def load_existing_save():
    try:
        data = request.get_json(silent=True) or {}
        save_id = data.get("save_id")
        if not save_id:
            return jsonify({"error": "Missing save_id"}), 400
            
        from engine.save_manager import load_save
        meta = load_save(save_id)
        
        if hasattr(runner, 'sessions_history'):
            runner.sessions_history.clear()
        reload_program_state()
            
        return jsonify({
            "status": "success",
            "save": meta
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/saves/delete', methods=['POST'])
@requires_auth
def delete_existing_save():
    try:
        data = request.get_json(silent=True) or {}
        save_id = data.get("save_id")
        if not save_id:
            return jsonify({"error": "Missing save_id"}), 400
            
        from engine.save_manager import delete_save
        success = delete_save(save_id)
        
        if hasattr(runner, 'sessions_history'):
            runner.sessions_history.clear()
        reload_program_state()
            
        return jsonify({
            "status": "success",
            "deleted": success
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _sync_active_character_snapshot_to_history(character_sheet: dict, session_id: str = None):
    """No-op: Single save state is authoritative; individual message state snapshots are deprecated."""
    pass


@app.route('/api/character/equip', methods=['POST'])
@requires_auth
def toggle_equip_item():
    try:
        data = request.get_json(silent=True) or {}
        item_name = data.get("item_name")
        should_equip = data.get("equip", True)
        req_session_id = data.get("session_id", "default")
        
        if not item_name:
            return jsonify({"error": "Missing item_name"}), 400
            
        from engine.save_manager import get_active_save_id
        from engine.character import load_character, save_character, equip_item, unequip_item
        
        save_id = get_active_save_id()
        sheet = load_character(save_id)
        
        if should_equip:
            sheet, success = equip_item(sheet, item_name)
        else:
            sheet, success = unequip_item(sheet, item_name)
            
        if success:
            save_character(save_id, sheet)
            _sync_active_character_snapshot_to_history(sheet, req_session_id)
            
        return jsonify({
            "status": "success",
            "character": sheet,
            "item_name": item_name,
            "equipped": should_equip
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def generate_inventory_item(description: str, model: str = None) -> dict:
    """Prompt the model to generate a structured RPG inventory item from a description."""
    import json, re, asyncio
    from engine.character import get_item_category, get_item_weight

    global runner
    if 'runner' not in globals() or runner is None:
        init_runner()

    system_instruction = (
        "You are an RPG inventory system. Convert the user item description into a single structured item JSON object.\n"
        "Return ONLY a valid JSON object without markdown code blocks, backticks, or explanatory text."
    )
    
    prompt = (
        f"Create a single RPG inventory item based on this concept or description:\n"
        f"\"{description.strip()}\"\n\n"
        f"Output JSON with exact fields:\n"
        f"{{\n"
        f"  \"name\": \"Formal Item Name\",\n"
        f"  \"type\": \"weapon\" or \"armor\" or \"shield\" or \"head\" or \"feet\" or \"hands\" or \"neck\" or \"ring\" or \"torch\" or \"potion\" or \"consumable\" or \"quest\" or \"misc\",\n"
        f"  \"weight\": 1.5,\n"
        f"  \"quantity\": 1,\n"
        f"  \"equipped\": false,\n"
        f"  \"description\": \"Flavor description of the item\"\n"
        f"}}"
    )

    raw_response = ""
    try:
        raw_response = asyncio.run(runner.generate_impersonation(prompt, system_instruction, model, temperature=0.3))
    except Exception as e:
        print(f"Error invoking model for item generation: {e}")

    item = None
    if raw_response:
        cleaned = re.sub(r'```(?:json)?\s*', '', raw_response)
        cleaned = re.sub(r'```', '', cleaned).strip()
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict) and parsed.get("name"):
                    raw_name = str(parsed.get("name", description.strip().title())).strip()
                    raw_type = str(parsed.get("type", "misc")).lower().strip()
                    try:
                        raw_weight = round(float(parsed.get("weight", 1.0)), 1)
                    except (ValueError, TypeError):
                        raw_weight = 1.0
                    try:
                        raw_qty = max(1, int(parsed.get("quantity", 1)))
                    except (ValueError, TypeError):
                        raw_qty = 1
                    item = {
                        "name": raw_name,
                        "type": raw_type,
                        "weight": raw_weight,
                        "quantity": raw_qty,
                        "equipped": bool(parsed.get("equipped", False)),
                        "description": str(parsed.get("description", "")).strip()
                    }
            except Exception as pe:
                print(f"Error parsing item JSON: {pe}")

    if not item:
        inferred_name = description.strip().title()
        temp_item = {"name": inferred_name}
        inferred_cat = get_item_category(temp_item) or "misc"
        temp_item["type"] = inferred_cat
        inferred_weight = get_item_weight(temp_item)
        item = {
            "name": inferred_name,
            "type": inferred_cat,
            "weight": inferred_weight,
            "quantity": 1,
            "equipped": False,
            "description": description.strip()
        }

    return item


@app.route('/api/character/item/create', methods=['POST'])
@app.route('/api/character/item/add', methods=['POST'])
@requires_auth
def create_character_item_route():
    try:
        data = request.get_json(silent=True) or {}
        description = data.get("description", "").strip()
        req_session_id = data.get("session_id", "default")
        model = data.get("model")

        if not description:
            return jsonify({"error": "Missing item description"}), 400

        item = generate_inventory_item(description, model=model)

        from engine.save_manager import get_active_save_id
        from engine.character import load_character, save_character, add_item

        save_id = get_active_save_id()
        sheet = load_character(save_id)

        sheet = add_item(sheet, item)
        save_character(save_id, sheet)
        _sync_active_character_snapshot_to_history(sheet, req_session_id)

        return jsonify({
            "status": "success",
            "character": sheet,
            "item": item,
            "message": f"Added {item['name']} to inventory."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/character/remove', methods=['POST'])
@app.route('/api/character/drop', methods=['POST'])
@requires_auth
def remove_character_item_route():
    try:
        data = request.get_json(silent=True) or {}
        item_name = data.get("item_name")
        quantity = int(data.get("quantity", 1))
        req_session_id = data.get("session_id", "default")
        
        if not item_name:
            return jsonify({"error": "Missing item_name"}), 400
            
        from engine.save_manager import get_active_save_id
        from engine.character import load_character, save_character, remove_item
        
        save_id = get_active_save_id()
        sheet = load_character(save_id)
        
        sheet, success = remove_item(sheet, item_name, quantity)
        if not success:
            return jsonify({"error": f"Item '{item_name}' not found in inventory."}), 404
            
        save_character(save_id, sheet)
        _sync_active_character_snapshot_to_history(sheet, req_session_id)
        
        return jsonify({
            "status": "success",
            "character": sheet,
            "removed": {"name": item_name, "quantity": quantity},
            "dropped": {"name": item_name, "quantity": quantity},
            "message": f"Removed {quantity}x {item_name}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/character/spell/remove', methods=['POST'])
@app.route('/api/character/forget_spell', methods=['POST'])
@requires_auth
def remove_character_spell_route():
    try:
        data = request.get_json(silent=True) or {}
        spell_name = data.get("spell_name")
        req_session_id = data.get("session_id", "default")
        
        if not spell_name:
            return jsonify({"error": "Missing spell_name"}), 400
            
        from engine.save_manager import get_active_save_id
        from engine.character import load_character, save_character, forget_spell
        
        save_id = get_active_save_id()
        sheet = load_character(save_id)
        
        sheet = forget_spell(sheet, spell_name)
        save_character(save_id, sheet)
        _sync_active_character_snapshot_to_history(sheet, req_session_id)
        
        return jsonify({
            "status": "success",
            "character": sheet,
            "removed_spell": spell_name,
            "message": f"Removed spell '{spell_name}'"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/character/gold/modify', methods=['POST'])
@app.route('/api/character/gold/remove', methods=['POST'])
@requires_auth
def modify_character_gold_route():
    try:
        data = request.get_json(silent=True) or {}
        amount = int(data.get("amount", 0))
        action = data.get("action", "remove")
        req_session_id = data.get("session_id", "default")
        
        from engine.save_manager import get_active_save_id
        from engine.character import load_character, save_character, spend_gold, add_gold
        
        save_id = get_active_save_id()
        sheet = load_character(save_id)
        
        if action == "set":
            sheet["gold"] = max(0, amount)
        elif action == "add":
            sheet = add_gold(sheet, amount)
        else:
            sheet = spend_gold(sheet, amount)
            
        save_character(save_id, sheet)
        _sync_active_character_snapshot_to_history(sheet, req_session_id)
        
        return jsonify({
            "status": "success",
            "character": sheet,
            "gold": sheet.get("gold", 0),
            "message": f"Updated gold balance to {sheet.get('gold', 0)}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def extract_profile_display_name(profile_id: str, content: str) -> str:
    if profile_id == "eternal_champion":
        return "Eternal Champion"
    for line in (content or "").splitlines():
        line = line.strip()
        if line.startswith("#"):
            raw = line.lstrip("#").strip()
            for prefix in ("CHARACTER:", "USER CONTEXT:", "USER PROFILE:"):
                if raw.upper().startswith(prefix):
                    raw = raw[len(prefix):].strip()
            if raw:
                return raw
    clean_id = re.sub(r'[\s_]+\d+$', '', profile_id).replace("_", " ").strip()
    return clean_id.title() if clean_id else "Eternal Champion"


@app.route('/api/user_profiles', methods=['GET'])
@requires_auth
def list_user_profiles():
    try:
        from engine.save_manager import list_saves, get_active_save_id, create_save
        from utils.program import get_active_user
        
        saves = list_saves()
        if not saves:
            create_save(save_id="eternal_champion")
            saves = list_saves()
            
        active_id = get_active_save_id()
        
        profiles = []
        for s in saves:
            from engine.save_manager import read_save
            bundle = read_save(s["id"])
            profile_text = bundle.get("profile") or f"A {s.get('race', 'Nord')} from Skyrim."
            profiles.append({
                "id": s["id"],
                "name": s.get("name") or s.get("character_name", s["id"]),
                "character_name": s.get("character_name", s["id"]),
                "content": profile_text,
                "gender": s.get("gender", "Male"),
                "race": s.get("race", "Nord"),
                "class": s.get("class", "Mage"),
                "level": s.get("level", 1),
                "gold": s.get("gold", 0),
                "location": s.get("current_location", "Imperial Dungeon")
            })

        return jsonify({"profiles": profiles, "active": active_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user_profiles/select', methods=['POST'])
@requires_auth
def select_user_profile():
    try:
        data = request.get_json(silent=True) or {}
        profile_id = data.get("profile_id")
        if not profile_id:
            return jsonify({"error": "Missing profile_id"}), 400
        
        from engine.save_manager import load_save
        load_save(profile_id)
        reload_program_state()
            
        return jsonify({"status": "success", "active": profile_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user_profiles/save', methods=['POST'])
@requires_auth
def save_user_profile():
    try:
        data = request.get_json(silent=True) or {}
        profile_id = data.get("profile_id")
        content = data.get("content")
        
        gender = data.get("gender")
        race = data.get("race")
        character_class = data.get("class")
        name = data.get("name")
        
        if not profile_id:
            return jsonify({"error": "Missing profile_id"}), 400
        if content is None:
            return jsonify({"error": "Missing content"}), 400
        
        # Sanitize profile_id
        profile_id = profile_id.strip().replace(' ', '_').lower()
        profile_id = re.sub(r'[^a-zA-Z0-9_\-]', '', profile_id)
        profile_id = re.sub(r'_+', '_', profile_id)
        if not profile_id:
            return jsonify({"error": "Invalid profile name"}), 400
            
        from utils.program import get_active_user
        from engine.save_manager import read_save, write_save, create_save
        from engine.character import update_character_identity
        
        display_name = name or extract_profile_display_name(profile_id, content)
        bundle = read_save(profile_id)
        bundle["profile"] = content
        
        sheet = bundle.get("character", {})
        sheet = update_character_identity(
            sheet=sheet,
            name=display_name,
            race=race,
            gender=gender,
            character_class=character_class,
            reset_vitals=True
        )
        bundle["character"] = sheet
        bundle.setdefault("meta", {})
        bundle["meta"]["character_name"] = display_name
        bundle["meta"]["name"] = display_name
        if race:
            bundle["meta"]["race"] = race
        if gender:
            bundle["meta"]["gender"] = gender
        if character_class:
            bundle["meta"]["class"] = character_class

        # If this save has no history, seed first_mes entry
        history = bundle.get("history", [])
        if not history:
            import uuid, time
            history = [{
                "id": f"first_mes_{uuid.uuid4().hex[:12]}",
                "role": "program",
                "timestamp": time.time()
            }]
            bundle["history"] = history

        write_save(profile_id, bundle)
            
        # Read active profile
        active_user = get_active_user()
        
        # If we edited the active profile, trigger hot reload immediately
        if profile_id == active_user:
            reload_program_state()
                
        return jsonify({"status": "success", "profile_id": profile_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user_profiles/delete', methods=['POST'])
@requires_auth
def delete_user_profile():
    try:
        data = request.get_json(silent=True) or {}
        profile_id = data.get("profile_id")
        if not profile_id:
            return jsonify({"error": "Missing profile_id"}), 400
            
        from utils.program import get_active_user, set_active_user
        from engine.save_manager import delete_save, set_active_save_id
        
        # Delete single-file save bound to this player profile
        deleted = delete_save(profile_id, force_delete=True)
        if not deleted:
            return jsonify({"error": f"Save '{profile_id}' does not exist"}), 404

        # If the deleted profile was active, switch active profile and save back to "eternal_champion"
        active_user = get_active_user()
                
        if profile_id == active_user:
            set_active_user("eternal_champion")
            set_active_save_id("eternal_champion")
            reload_program_state()
                
        return jsonify({"status": "success", "deleted": profile_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user_profiles/rename', methods=['POST'])
@requires_auth
def rename_user_profile():
    try:
        data = request.get_json(silent=True) or {}
        old_profile_id = data.get("old_profile_id")
        new_name = (data.get("new_profile_name") or "").strip()
        
        if not old_profile_id or not new_name:
            return jsonify({"error": "Missing old_profile_id or new_profile_name"}), 400
            
        from engine.save_manager import SAVES_DIR, read_save, write_save, set_active_save_id, sync_save_meta
        from utils.program import get_active_user, set_active_user
        
        old_file = SAVES_DIR / f"{old_profile_id}.json"
        if not old_file.exists():
            return jsonify({"error": f"Save '{old_profile_id}' does not exist"}), 404
            
        # Determine new save ID preserving slot suffix if present
        clean_prefix = "".join(c for c in new_name.lower().replace(" ", "_").replace("-", "_") if c.isalnum() or c == "_")
        clean_prefix = re.sub(r'_+', '_', clean_prefix).strip('_') or "hero"
        
        slot_match = re.search(r'_(\d{3,})$', old_profile_id)
        slot_suffix = f"_{slot_match.group(1)}" if slot_match else ""
        new_save_id = f"{clean_prefix}{slot_suffix}" if slot_suffix else clean_prefix
        
        bundle = read_save(old_profile_id)
        bundle.setdefault("meta", {})
        bundle["meta"]["character_name"] = new_name
        bundle["meta"]["name"] = new_name
        if "character" in bundle and isinstance(bundle["character"], dict):
            bundle["character"]["name"] = new_name
            
        write_save(new_save_id, bundle)
        
        if new_save_id != old_profile_id and old_file.exists():
            old_file.unlink(missing_ok=True)
            
        sync_save_meta(new_save_id)
        
        # If the renamed save was active, update active pointers
        active_user = get_active_user()
        if old_profile_id == active_user:
            set_active_user(new_save_id)
            set_active_save_id(new_save_id)
            reload_program_state()
                
        return jsonify({"status": "success", "profile_id": new_save_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500




def generate_character_theme(main_color, accent_color_a=None, accent_color_b=None):
    hex_clean = main_color.lstrip('#')
    r = int(hex_clean[0:2], 16)
    g = int(hex_clean[2:4], 16)
    b = int(hex_clean[4:6], 16)
    
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    btn_text = "#121214" if brightness > 140 else "#ffffff"
    
    if not accent_color_a:
        accent_r = min(255, int(r + (255 - r) * 0.25))
        accent_g = min(255, int(g + (255 - g) * 0.25))
        accent_b = min(255, int(b + (255 - b) * 0.25))
        accent_color_a = f"#{accent_r:02x}{accent_g:02x}{accent_b:02x}"
    if not accent_color_b:
        accent_color_b = main_color
        
    return {
        "primary_accent": main_color,
        "main_color": main_color,
        "accent_color_a": accent_color_a,
        "accent_color_b": accent_color_b,
        "primary_glow": f"rgba({r}, {g}, {b}, 0.08)",
        "program_bubble": f"rgba({24 + int(r*0.04)}, {24 + int(g*0.04)}, {28 + int(b*0.04)}, 0.85)",
        "send_btn_hover": f"rgba({20 + int(r*0.12)}, {20 + int(g*0.12)}, {22 + int(b*0.12)}, 0.75)",
        "accent_green": accent_color_a,
        "quote_blue": main_color,
        "primary_btn_text": btn_text
    }

# Obsolete sprite and theme color generation functions removed


def generate_character_json(name, description, personality, scenario, first_mes, model):
    """Ask the LLM to produce chara_card_v3-compatible fields for a new program."""
    import os, json
    remote_key = os.getenv("REMOTE_API_KEY")
    remote_cloud_url = os.getenv("REMOTE_CLOUD_URL")
    is_remote_configured = bool(
        remote_key and remote_key.strip() and remote_key != "your_remote_api_key_here" and
        remote_cloud_url and remote_cloud_url.strip() and remote_cloud_url != "your_remote_cloud_url_here"
    )

    prompt = f"""Design a SillyTavern chara_card_v3 character profile from the description below.

Input:
  Name: {name}
  Description: {description}
  Personality hint: {personality or 'not specified'}
  Scenario hint: {scenario or 'not specified'}
  First message hint: {first_mes or 'not specified'}

Output a single JSON object with EXACTLY these keys:
{{
  "description": "2-4 sentence narrative bio. No physical appearance.",
  "personality": "One word (e.g. Devoted, Sassy, Stoic).",
  "scenario": "Short scene-setting sentence (one sentence).",
  "first_mes": "In-character opening message (1-2 sentences, first person).",
  "system_prompt": "Concise response style directive (e.g. contractions, tone, length).",
  "image_positive": "Comma-separated Stable Diffusion tags for ONLY physical appearance (e.g. silver hair, purple eyes, fair skin).",
  "image_negative": "Comma-separated SD negative tags to exclude (e.g. extra limbs, bad anatomy).",
  "main_color": "#RRGGBB — a hex color representing this character.",
  "inversion": {{
    "intimate": "How they behave when intimate/warm.",
    "excited": "How they behave when excited/playful.",
    "intense": "How they behave when intense/focused.",
    "sad": "How they behave when sad/empathetic."
  }}
}}"""

    raw_response = None
    from utils.models import is_local_model
    use_local = is_local_model(model)

    if use_local:
        try:
            import httpx
            local_url = os.getenv("REMOTE_SERVER_URL", "http://127.0.0.1:1234/v1/chat/completions")
            local_model = model if (model and model != 'local-llm') else os.getenv("LOCAL_MODEL_NAME", "local-llm")
            payload = {
                "model": local_model,
                "messages": [
                    {"role": "system", "content": "You output valid JSON character cards."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5,
                "response_format": {"type": "json_object"}
            }
            res = httpx.post(local_url, json=payload, headers={"Content-Type": "application/json"}, timeout=60.0)
            if res.status_code == 200:
                raw_response = res.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"Error calling local model for card generation: {e}")
    else:
        if is_remote_configured:
            try:
                import requests
                from variables import DEFAULT_REMOTE_MODEL
                target_model = model if model else DEFAULT_REMOTE_MODEL
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {remote_key}"}
                payload = {
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": "You output valid JSON character cards."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.5,
                    "response_format": {"type": "json_object"}
                }
                res = requests.post(remote_cloud_url, json=payload, headers=headers, timeout=60.0)
                if res.status_code == 200:
                    raw_response = res.json()['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(f"Error calling remote model for card generation: {e}")

    parsed = {}
    if raw_response:
        try:
            cleaned = raw_response.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
            parsed = json.loads(cleaned)
        except Exception as e:
            print(f"Failed to parse card JSON: {e}. Raw: {raw_response}")

    # Build a chara_card_v3 dict. Helper keys _inversion and _colors are
    # popped by finalize_imported_program before writing to disk.
    card = {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "name": name or parsed.get("name") or "Program",
            "description": parsed.get("description") or description or f"{name} is a new program.",
            "personality": parsed.get("personality") or personality or "Friendly",
            "scenario": parsed.get("scenario") or scenario or "A comfortable room.",
            "first_mes": parsed.get("first_mes") or first_mes or f"Hello, I'm {name}.",
            "mes_example": "",
            "system_prompt": parsed.get("system_prompt") or "Speak naturally using contractions. Be warm and concise.",
            "post_history_instructions": "",
            "creator_notes": "",
            "tags": [],
            "creator": "LM-Arena",
            "character_version": "1.0",
            "alternate_greetings": [],
            "extensions": {
                "arena": {
                    "program_id": "",  # filled by finalize_imported_program
                    "image_details": {
                        "positive": parsed.get("image_positive") or f"solo, {name}",
                        "negative": parsed.get("image_negative") or "extra limbs, bad anatomy, deformed"
                    }
                }
            }
        },
        # Helper keys consumed by finalize_imported_program
        "_inversion": parsed.get("inversion") or {
            "intimate": f"{name} is now deeply affectionate and tender.",
            "excited": f"{name} is now playful and energetic.",
            "intense": f"{name} is now focused and direct.",
            "sad": f"{name} is now empathetic and gentle."
        },
        "_colors": {"main_color": parsed.get("main_color") or "#38bdf8"},
    }
    return card


def finalize_imported_program(program_path, program_id, card_json):
    """Write inversion, theme, portraits dir, and chara_card_v3 JSON for a new program."""
    # Pop helper keys (not part of the card spec)
    inversion = card_json.pop("_inversion", None) or card_json.pop("inversion", None) or {}
    colors = card_json.pop("_colors", None) or card_json.pop("colors", None) or {}

    # Write inversion.json
    with open(os.path.join(program_path, 'inversion.json'), "w", encoding="utf-8") as f:
        json.dump(inversion, f, indent=2, ensure_ascii=False)

    # Generate theme from main_color
    main_color = colors.get("main_color", "#38bdf8")
    theme_data = generate_character_theme(main_color)
    with open(os.path.join(program_path, 'theme.json'), "w", encoding="utf-8") as tf:
        json.dump(theme_data, tf, indent=2, ensure_ascii=False)

    os.makedirs(os.path.join(program_path, 'portraits'), exist_ok=True)

    # Stamp program_id into the arena extension
    if card_json.get("data"):
        exts = card_json["data"].setdefault("extensions", {})
        exts.setdefault("arena", {})["program_id"] = program_id
    else:
        # Legacy flat format fallback
        card_json["program_id"] = program_id

    with open(os.path.join(program_path, f"{program_id}.json"), "w", encoding="utf-8") as f:
        json.dump(card_json, f, indent=2, ensure_ascii=False)


@app.route('/api/programs/<program_id>/export/card', methods=['GET'])
@requires_auth
def export_program_card(program_id):
    """Download the program's card as a SillyTavern-compatible JSON file."""
    try:
        card_path = os.path.join(base_dir, 'core', 'programs', program_id, f'{program_id}.json')
        if not os.path.exists(card_path):
            return jsonify({'error': 'Program not found'}), 404
        with open(card_path, encoding='utf-8') as f:
            card_data = json.load(f)
        name = card_data.get('data', card_data).get('name', program_id)
        safe_name = re.sub(r'[^\w\- ]', '', name).strip().replace(' ', '_') or program_id
        # Export only ST-spec keys — strip Arena internals from root
        export_data = {k: v for k, v in card_data.items() if k in ('spec', 'spec_version', 'data')}
        resp = make_response(json.dumps(export_data, indent=2, ensure_ascii=False))
        resp.headers['Content-Type'] = 'application/json'
        resp.headers['Content-Disposition'] = f'attachment; filename="{safe_name}.json"'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/<program_id>/export/lorebook', methods=['GET'])
@requires_auth
def export_program_lorebook(program_id):
    """Download the embedded character_book as a standalone lorebook JSON."""
    try:
        card_path = os.path.join(base_dir, 'core', 'programs', program_id, f'{program_id}.json')
        if not os.path.exists(card_path):
            return jsonify({'error': 'Program not found'}), 404
        with open(card_path, encoding='utf-8') as f:
            card_data = json.load(f)
        cb = card_data.get('data', card_data).get('character_book')
        if not cb:
            return jsonify({'error': 'No embedded lorebook found'}), 404
        name = card_data.get('data', card_data).get('name', program_id)
        safe_name = re.sub(r'[^\w\- ]', '', name).strip().replace(' ', '_') or program_id
        resp = make_response(json.dumps(cb, indent=2, ensure_ascii=False))
        resp.headers['Content-Type'] = 'application/json'
        resp.headers['Content-Disposition'] = f'attachment; filename="{safe_name}_lorebook.json"'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/import/tavern', methods=['POST'])
@requires_auth
def import_tavern_program():
    try:
        if 'card' not in request.files:
            return jsonify({'error': 'No card file provided'}), 400

        file = request.files['card']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        import re, base64
        from PIL import Image

        temp_dir = os.path.join(base_dir, 'backups')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, 'temp_tavern_card.png')
        file.save(temp_path)

        try:
            with Image.open(temp_path) as img:
                chara_data = None
                for key in ('chara', 'ccv3', 'Character'):
                    if key in img.info:
                        chara_data = img.info[key]
                        break
                if not chara_data:
                    for key, val in img.info.items():
                        if isinstance(val, str) and len(val) > 20:
                            try:
                                test_json = json.loads(val)
                                if isinstance(test_json, dict) and ("name" in test_json or "data" in test_json):
                                    chara_data = val
                                    break
                            except Exception:
                                try:
                                    decoded = base64.b64decode(val).decode('utf-8')
                                    test_json = json.loads(decoded)
                                    if isinstance(test_json, dict) and ("name" in test_json or "data" in test_json):
                                        chara_data = val
                                        break
                                except Exception:
                                    pass

                if not chara_data:
                    raise ValueError("No character metadata chunk found in PNG card.")

                try:
                    chara = json.loads(base64.b64decode(chara_data).decode('utf-8'))
                except Exception:
                    chara = json.loads(chara_data)

        except Exception as e:
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except Exception: pass
            return jsonify({'error': f"Failed to parse Tavern card: {str(e)}"}), 400

        finally:
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except Exception: pass

        # --- Convert to chara_card_v3 (bypass LLM — use the card data directly) ---
        spec = chara.get('spec', '')
        if spec == 'chara_card_v3':
            # Already v3 — use verbatim
            card_v3 = chara
            data_block = card_v3.get('data', {})
        else:
            # v1 / v2 flat or wrapped — normalise to v3
            data_block = chara.get('data', chara)
            card_v3 = {
                "spec": "chara_card_v3",
                "spec_version": "3.0",
                "data": {
                    "name": data_block.get("name", "Program"),
                    "description": data_block.get("description", ""),
                    "personality": data_block.get("personality", ""),
                    "scenario": data_block.get("scenario", ""),
                    "first_mes": data_block.get("first_mes", ""),
                    "mes_example": data_block.get("mes_example", ""),
                    "system_prompt": data_block.get("system_prompt", ""),
                    "post_history_instructions": data_block.get("post_history_instructions", ""),
                    "creator_notes": data_block.get("creator_notes", ""),
                    "tags": data_block.get("tags", []),
                    "creator": data_block.get("creator", ""),
                    "character_version": data_block.get("character_version", "1.0"),
                    "alternate_greetings": data_block.get("alternate_greetings", []),
                    "character_book": data_block.get("character_book"),
                    "extensions": data_block.get("extensions", {}),
                }
            }
            # Remove None character_book
            if card_v3["data"]["character_book"] is None:
                del card_v3["data"]["character_book"]

        name = card_v3["data"].get("name", "Program").strip()
        program_id = re.sub(r'[^a-zA-Z0-9_\-]', '', name).lower() or ("program_" + str(int(time.time())))
        program_path = os.path.join(base_dir, 'core', 'programs', program_id)
        if os.path.exists(program_path):
            return jsonify({'error': f"Program folder '{program_id}' already exists"}), 400
        os.makedirs(program_path, exist_ok=True)

        # Ensure arena extension block
        exts = card_v3["data"].setdefault("extensions", {})
        arena = exts.setdefault("arena", {})
        arena["program_id"] = program_id
        if "image_details" not in arena:
            arena["image_details"] = {"positive": "", "negative": ""}

        # Derive inversion and color from existing extensions or use defaults
        inversion = arena.pop("inversion", None) or {
            "intimate": f"{name} is now deeply affectionate and tender.",
            "excited": f"{name} is now playful and energetic.",
            "intense": f"{name} is now focused and direct.",
            "sad": f"{name} is now empathetic and gentle."
        }
        main_color = arena.pop("main_color", None) or "#38bdf8"

        card_v3["_inversion"] = inversion
        card_v3["_colors"] = {"main_color": main_color}

        finalize_imported_program(program_path, program_id, card_v3)
        return jsonify({'status': 'success', 'program_id': program_id, 'name': name})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs/import/describe', methods=['POST'])
@requires_auth
def import_describe_program():
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        model = data.get('model', '').strip()
        
        if not name or not description:
            return jsonify({'error': 'Name and description are required'}), 400
            
        program_id = re.sub(r'[^a-zA-Z0-9_\-]', '', name).lower()
        if not program_id:
            program_id = "program_" + str(int(time.time()))
            
        program_path = os.path.join(base_dir, 'core', 'programs', program_id)
        if os.path.exists(program_path):
            return jsonify({'error': f"Program folder '{program_id}' already exists"}), 400
            
        os.makedirs(program_path, exist_ok=True)
        
        # Call consolidated JSON generator
        card_json = generate_character_json(name, description, "", "", "", model)
        
        # Finalize program files (inversion, theme, portraits, and JSON profile)
        finalize_imported_program(program_path, program_id, card_json)
            
        return jsonify({'status': 'success', 'program_id': program_id, 'name': name})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# --- Server-Sent Events (SSE) for Live Connection Status ---
import queue as _queue

_sse_clients = []
_sse_clients_lock = threading.Lock()
_last_broadcast_state = {}

def _get_current_status():
    """Build the combined connection status payload."""
    from utils import local_llm_manager, comfy_manager
    remote_key = os.getenv("REMOTE_API_KEY")
    remote_cloud_url = os.getenv("REMOTE_CLOUD_URL")
    is_remote_configured = bool(
        remote_key and remote_key.strip() and remote_key != "your_remote_api_key_here" and
        remote_cloud_url and remote_cloud_url.strip() and remote_cloud_url != "your_remote_cloud_url_here"
    )
    
    # Load temperature dynamically
    temperature = 0.95
    try:
        from variables import VARIABLES_DIR
        settings_path = os.path.join(VARIABLES_DIR, "project_settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
                temperature = settings.get("temperature", 0.95)
    except Exception:
        pass
        
    comfy_running_state = comfy_manager.check_comfy_running(force_refresh=True)
    if not comfy_running_state and getattr(comfy_manager, '_starting', False):
        comfy_running_state = "starting"
        
    return {
        "remote_configured": is_remote_configured,
        "remote_model": os.getenv("REMOTE_MODEL", "gemini-3.1-flash-lite"),
        "remote_url": remote_cloud_url,
        "local_online": local_llm_manager.check_status(),
        "local_installed": local_llm_manager.check_installed(),
        "comfy_installed": comfy_manager.check_comfy_installed(),
        "comfy_running": comfy_running_state,
        "temperature": temperature,
        "env_path": os.path.abspath(os.path.join(base_dir, '.env')),
    }

def broadcast_status():
    """Push current status to all connected SSE clients (only if state changed)."""
    global _last_broadcast_state
    status = _get_current_status()
    # Deduplicate: only broadcast when state actually changed
    if status == _last_broadcast_state:
        return
    _last_broadcast_state = status.copy()
    data = json.dumps({"type": "connection_status", "status": status})
    msg = f"event: connection_status\ndata: {data}\n\n"
    with _sse_clients_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except _queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)

def _status_monitor():
    """Background thread that detects external state changes (crashes, manual stops)."""
    while True:
        time.sleep(5)
        try:
            broadcast_status()
        except Exception:
            pass

_monitor_thread = threading.Thread(target=_status_monitor, daemon=True)
_monitor_thread.start()

@app.route('/api/events/status')
@requires_auth
def sse_status_stream():
    """SSE endpoint for live connection status updates."""
    q = _queue.Queue(maxsize=50)
    with _sse_clients_lock:
        _sse_clients.append(q)

    def stream():
        try:
            # Send initial status immediately
            status = _get_current_status()
            data = json.dumps({"type": "connection_status", "status": status})
            yield f"event: connection_status\ndata: {data}\n\n"
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield msg
                except _queue.Empty:
                    # Keepalive comment to prevent proxy/browser timeout
                    yield ":\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_clients_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)

    return Response(stream(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    })


# --- Headless Local LLM & Hugging Face Integration API ---
from utils import local_llm_manager
from utils import comfy_manager

# Wire SSE broadcast callbacks into both managers
from utils import local_runner
local_runner._on_status_change = broadcast_status
comfy_manager._on_status_change = broadcast_status

@app.route('/api/local_llm/status', methods=['GET'])
@requires_auth
def local_llm_status():
    installed = local_llm_manager.check_installed()
    online = local_llm_manager.check_status()
    loaded_models = []
    if online is True:
        from utils.models import fetch_local_models
        loaded_models = [m["value"] for m in fetch_local_models()]
    
    downloaded_models = local_llm_manager.list_local_models()
    local_llm_manager.update_download_statuses()
    
    return jsonify({
        "installed": installed,
        "online": online,
        "loaded_models": loaded_models,
        "downloaded_models": downloaded_models,
        "download_status": local_llm_manager.download_status
    })

@app.route('/api/local_llm/install', methods=['POST'])
@requires_auth
def local_llm_install():
    success, message = local_llm_manager.install_server()
    return jsonify({"success": success, "message": message})

@app.route('/api/local_llm/search', methods=['GET'])
@requires_auth
def local_llm_search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"results": []})
    results = local_llm_manager.search_huggingface_repos(query)
    return jsonify({"results": results})

@app.route('/api/local_llm/huggingface/files', methods=['GET'])
@requires_auth
def local_llm_hf_files():
    repo_id = request.args.get('repo_id', '').strip()
    if not repo_id:
        return jsonify({"error": "Missing repo_id"}), 400
    files = local_llm_manager.get_huggingface_repo_files(repo_id)
    return jsonify({"files": files})

@app.route('/api/local_llm/download', methods=['POST'])
@requires_auth
def local_llm_download():
    model_name = request.json.get('model_name')
    quantization = request.json.get('quantization')
    if not model_name:
        return jsonify({"error": "Missing model_name"}), 400
    success, message = local_llm_manager.trigger_download(model_name, quantization)
    return jsonify({"success": success, "message": message})

@app.route('/api/local_llm/load', methods=['POST'])
@requires_auth
def local_llm_load():
    model_name = request.json.get('model_name')
    if not model_name:
        return jsonify({"error": "Missing model_name"}), 400
    success, message = local_llm_manager.load_local_model(model_name)
    return jsonify({"success": success, "message": message})

@app.route('/api/local_llm/unload', methods=['POST'])
@requires_auth
def local_llm_unload():
    model_name = request.json.get('model_name')
    success, message = local_llm_manager.unload_local_model(model_name)
    return jsonify({"success": success, "message": message})

@app.route('/api/local_llm/delete', methods=['POST'])
@requires_auth
def local_llm_delete():
    model_name = request.json.get('model_name')
    if not model_name:
        return jsonify({"error": "Missing model_name"}), 400
    success, message = local_llm_manager.delete_local_model(model_name)
    return jsonify({"success": success, "message": message})

@app.route('/api/local_llm/start', methods=['POST'])
@requires_auth
def local_llm_start():
    success, message = local_llm_manager.start_server()
    broadcast_status()
    return jsonify({"success": success, "message": message})

@app.route('/api/local_llm/stop', methods=['POST'])
@requires_auth
def local_llm_stop():
    success, message = local_llm_manager.stop_server()
    broadcast_status()
    return jsonify({"success": success, "message": message})


# --- Headless ComfyUI & Dependency Resolver API ---

@app.route('/api/comfy/status', methods=['GET'])
@requires_auth
def comfy_status():
    installed = comfy_manager.check_comfy_installed()
    running = comfy_manager.check_comfy_running()
    if not running and getattr(comfy_manager, '_starting', False):
        running = "starting"
    return jsonify({
        "installed": installed,
        "running": running,
        "resolution_status": comfy_manager.resolution_status
    })

@app.route('/api/comfy/install', methods=['POST'])
@requires_auth
def comfy_install():
    success, message = comfy_manager.trigger_install_comfy()
    return jsonify({"success": success, "message": message})

@app.route('/api/comfy/start', methods=['POST'])
@requires_auth
def comfy_start():
    success, message = comfy_manager.start_comfy_server()
    broadcast_status()
    return jsonify({"success": success, "message": message})

@app.route('/api/comfy/stop', methods=['POST'])
@requires_auth
def comfy_stop():
    success, message = comfy_manager.stop_comfy_server()
    broadcast_status()
    return jsonify({"success": success, "message": message})

@app.route('/api/comfy/resolve_workflow', methods=['POST'])
@requires_auth
def comfy_resolve_workflow():
    workflow_json = request.json.get("workflow_json")
    if not workflow_json:
        try:
            from variables import PROGRAMS_DIR, COMFYUI_CHECKPOINT
            from utils.program import get_active_program
            active_program = get_active_program()
            
            combined_workflow = {}
            
            # Read ImageWorkflow.json
            image_path = os.path.normpath(os.path.join(
                PROGRAMS_DIR, active_program, "portraits", "ImageWorkflow.json"
            ))
            if not os.path.exists(image_path):
                image_path = os.path.normpath(os.path.join(
                    base_dir, "core", "skills", "portrait_generation", "ImageWorkflow.json"
                ))
                
            if os.path.exists(image_path):
                with open(image_path, "r", encoding="utf-8") as f:
                    try:
                        image_wf = json.load(f)
                        resolved_checkpoint = os.getenv("COMFYUI_CHECKPOINT", COMFYUI_CHECKPOINT)
                        image_str = json.dumps(image_wf).replace("%model%", resolved_checkpoint)
                        image_wf = json.loads(image_str)
                        for k, v in image_wf.items():
                            combined_workflow[f"image_{k}"] = v
                    except Exception as je1:
                        print(f"Error parsing ImageWorkflow.json for resolution: {je1}")
            
            # Read VideoWorkflow.json
            video_path = os.path.normpath(os.path.join(
                PROGRAMS_DIR, active_program, "portraits", "VideoWorkflow.json"
            ))
            if not os.path.exists(video_path):
                video_path = os.path.normpath(os.path.join(
                    base_dir, "core", "skills", "portrait_generation", "VideoWorkflow.json"
                ))
                
            if os.path.exists(video_path):
                with open(video_path, "r", encoding="utf-8") as f:
                    try:
                        video_wf = json.load(f)
                        for k, v in video_wf.items():
                            combined_workflow[f"video_{k}"] = v
                    except Exception as je2:
                        print(f"Error parsing VideoWorkflow.json for resolution: {je2}")
            
            if combined_workflow:
                workflow_json = json.dumps(combined_workflow)
        except Exception as e:
            return jsonify({"error": f"Failed to read program workflows: {e}"}), 500
            
    if not workflow_json:
        return jsonify({"error": "No workflow configuration found to resolve."}), 400
        
    success, message = comfy_manager.trigger_dependency_resolution(workflow_json)
    return jsonify({"success": success, "message": message})


# --- Headless ComfyUI Checkpoint Management APIs ---

@app.route('/api/comfy/checkpoints', methods=['GET'])
@requires_auth
def comfy_checkpoints():
    try:
        from utils.comfy_manager import list_local_checkpoints
        checkpoints = list_local_checkpoints()
        active = os.getenv("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors")
        return jsonify({
            "checkpoints": checkpoints,
            "active": active
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/comfy/checkpoints/select', methods=['POST'])
@requires_auth
def comfy_select_checkpoint():
    try:
        checkpoint = request.json.get("checkpoint")
        if not checkpoint:
            return jsonify({"error": "Missing checkpoint parameter"}), 400
            
        os.environ["COMFYUI_CHECKPOINT"] = checkpoint
        
        # Persist to .env
        env_path = os.path.join(base_dir, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith('COMFYUI_CHECKPOINT='):
                    lines[i] = f"COMFYUI_CHECKPOINT={checkpoint}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"\nCOMFYUI_CHECKPOINT={checkpoint}\n")
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
                
        return jsonify({"status": "success", "active": checkpoint})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/comfy/checkpoints/search', methods=['GET'])
@requires_auth
def comfy_search_checkpoints():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"results": []})
    from utils.comfy_manager import search_huggingface_checkpoints
    results = search_huggingface_checkpoints(query)
    return jsonify({"results": results})

@app.route('/api/comfy/checkpoints/download', methods=['POST'])
@requires_auth
def comfy_download_checkpoint():
    url = request.json.get("url")
    filename = request.json.get("filename")
    if not url or not filename:
        return jsonify({"error": "Missing url or filename"}), 400
        
    from utils.comfy_manager import trigger_checkpoint_download
    success, message = trigger_checkpoint_download(url, filename)
    return jsonify({"success": success, "message": message})

@app.route('/api/comfy/checkpoints/download_status', methods=['GET'])
@requires_auth
def comfy_checkpoint_download_status():
    from utils.comfy_manager import checkpoint_download_status
    return jsonify(checkpoint_download_status)


# Prewarming is now handled on the first request inside start_prewarm_on_first_request()

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    
    ssl_context = None
    use_https = os.getenv('USE_HTTPS', 'false').lower() == 'true'
    ssl_cert = os.getenv('SSL_CERT')
    ssl_key = os.getenv('SSL_KEY')
    
    if ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_context = (ssl_cert, ssl_key)
        print(f"[*] Starting server with SSL certificate: {ssl_cert}")
    elif use_https:
        try:
            import OpenSSL
            ssl_context = 'adhoc'
            print("[*] Starting server with ad-hoc SSL certificate")
        except ImportError:
            print("[!] pyOpenSSL is not installed. To run with ad-hoc SSL, please run: pip install pyopenssl")
            print("[!] Falling back to HTTP...")
            
    # Open the browser only on the initial startup.
    # The parent process runs exactly once on startup, whereas the child worker process restarts on file changes.
    if os.environ.get('OPEN_BROWSER', '').lower() == 'true' and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        browser_host = host if host != '0.0.0.0' else '127.0.0.1'
        protocol = 'https' if ssl_context else 'http'
        url = f"{protocol}://{browser_host}:{port}"
        
        def open_browser():
            import webbrowser
            print(f"[*] Automatically opening browser to: {url}")
            webbrowser.open(url)
            
        threading.Timer(1.5, open_browser).start()
            
    app.run(
        host=host,
        port=port,
        debug=True,
        ssl_context=ssl_context,
        use_reloader=True,
        reloader_type='stat',  # Use stable stat reloader to avoid false-alarm watchdog access events on Windows
        exclude_patterns=[
            '*.venv*', '*\\.venv\\*', '*\\site-packages\\*', 
            '*AppData*', '*site-packages*', '*__pycache__*',
            '*.env', 'active_program.txt', '*.txt', '*.db', '*.json'
        ]
    )