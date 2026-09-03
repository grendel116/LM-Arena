import os
import subprocess
import requests
import time
import uuid
import functools
import threading
import contextvars

from variables.settings import COMFYUI_SERVER_URL, COMFYUI_CHECKPOINT, COMFYUI_VAE, VARIABLES_DIR, FOLLOWERS_DIR


active_running_tools = {}
_active_tools_lock = threading.Lock()

current_session_id = contextvars.ContextVar('current_session_id', default='eternal_champion')
session_tool_calls_lock = threading.Lock()
session_tool_calls = {}

def track_tool_activity(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        sess_id = current_session_id.get()
        call_id = f"call_{int(time.time()*1000)}_{uuid.uuid4().hex[:4]}"
        
        # Build argument representation for display
        args_rep = []
        if args:
            args_rep.extend([repr(x) for x in args])
        if kwargs:
            args_rep.extend([f"{k}={repr(v)}" for k, v in kwargs.items()])
        args_str = ", ".join(args_rep)
        
        tool_call_info = {
            'id': call_id,
            'name': func.__name__,
            'args': args_str,
            'status': 'running',
            'response': '',
            'start_time': time.time(),
            'duration': 0.0
        }
        
        with session_tool_calls_lock:
            if sess_id not in session_tool_calls:
                session_tool_calls[sess_id] = []
            session_tool_calls[sess_id].append(tool_call_info)

        with _active_tools_lock:
            active_running_tools[func.__name__] = active_running_tools.get(func.__name__, 0) + 1
            
        start_time = time.time()
        try:
            res = func(*args, **kwargs)
            duration = round(time.time() - start_time, 2)
            with session_tool_calls_lock:
                if sess_id in session_tool_calls:
                    for tc in session_tool_calls[sess_id]:
                        if tc['id'] == call_id:
                            tc['status'] = 'completed'
                            tc['response'] = str(res)[:1000]
                            tc['duration'] = duration
            return res
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            with session_tool_calls_lock:
                if sess_id in session_tool_calls:
                    for tc in session_tool_calls[sess_id]:
                        if tc['id'] == call_id:
                            tc['status'] = 'failed'
                            tc['response'] = f"Error: {e}"
                            tc['duration'] = duration
            raise
        finally:
            with _active_tools_lock:
                if func.__name__ in active_running_tools:
                    active_running_tools[func.__name__] -= 1
                    if active_running_tools[func.__name__] <= 0:
                        active_running_tools.pop(func.__name__, None)
    return wrapper

def get_comfy_checkpoints(comfy_url: str) -> list:
    try:
        response = requests.get(f"{comfy_url}/object_info", timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            ckpt_loader = data.get("CheckpointLoaderSimple", {})
            ckpt_names = ckpt_loader.get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
            if isinstance(ckpt_names, list):
                return ckpt_names
    except Exception as e:
        print(f"[DEBUG] Failed to fetch checkpoints from ComfyUI: {e}", flush=True)
    return []

def get_comfy_vaes(comfy_url: str) -> list:
    try:
        response = requests.get(f"{comfy_url}/object_info", timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            vae_loader = data.get("VAELoader", {})
            vae_names = vae_loader.get("input", {}).get("required", {}).get("vae_name", [[]])[0]
            if isinstance(vae_names, list):
                return vae_names
    except Exception as e:
        print(f"[DEBUG] Failed to fetch VAEs from ComfyUI: {e}", flush=True)
    return []

def format_comfy_validation_error(error_json: dict) -> str:
    try:
        details = error_json.get("error", {}).get("details", {})
        node_errors = details.get("node_errors", {})
        if not node_errors:
            return None
            
        messages = []
        for node_id, error_info in node_errors.items():
            class_type = error_info.get("class_type", "Node")
            errors = error_info.get("errors", [])
            for err in errors:
                err_msg = err.get("message", "")
                err_details = err.get("details", "")
                
                if "LoRA not found" in err_msg or class_type == "LoraLoader":
                    messages.append(
                        f"**Missing LoRA**: The required LoRA file `{err_details}` was not found.\n"
                        f"Please download it and place it in your `ComfyUI/models/loras/` directory."
                    )
                elif "Checkpoint not found" in err_msg or class_type == "CheckpointLoaderSimple":
                    messages.append(
                        f"**Missing Checkpoint**: The required model checkpoint `{err_details}` was not found.\n"
                        f"Please place it in your `ComfyUI/models/checkpoints/` directory, or update your `.env` configuration."
                    )
                elif "VAE not found" in err_msg or class_type == "VAELoader":
                    messages.append(
                        f"**Missing VAE**: The required VAE file `{err_details}` was not found.\n"
                        f"Please place it in your `ComfyUI/models/vae/` directory, or update your `.env` configuration."
                    )
                else:
                    messages.append(f"**Node Validation Error** (Node {node_id}, Type `{class_type}`): {err_msg}")
                    
        if messages:
            return "\n\n".join(messages)
    except Exception:
        pass
    return None


@track_tool_activity
def apply_comfy_workflow(workflow_path: str, parameters: dict, save_path: str, session_id: str = None) -> str:
    """Executes a specified ComfyUI workflow JSON template with custom parameter mappings and saves the output.

    Args:
        workflow_path: Path to the workflow JSON file.
        parameters: Dictionary of placeholder keys and their replacement values.
        save_path: Path where the generated image should be saved.
        session_id: Optional session identifier used to honour cancellation requests.

    Returns:
        The filesystem path of the saved image, or an error message.
    """
    import os
    import json
    import requests
    import time

    if not os.path.exists(workflow_path):
        return f"Error: Workflow template not found at '{workflow_path}'"

    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
    except Exception as e:
        return f"Error reading workflow template: {e}"

    # Recursive replacement helper
    def replace_placeholders(obj):
        if isinstance(obj, dict):
            res_dict = {}
            for k, v in obj.items():
                if k == "appearance":
                    continue
                res_dict[k] = replace_placeholders(v)
            return res_dict
        elif isinstance(obj, list):
            return [replace_placeholders(x) for x in obj]
        elif isinstance(obj, str):
            for placeholder, val in parameters.items():
                if placeholder in obj:
                    if obj == placeholder:
                        return val
                    obj = obj.replace(placeholder, str(val))
            return obj
        return obj

    populated_workflow = replace_placeholders(workflow)
    comfy_url = COMFYUI_SERVER_URL

    def _cancel_comfy_job(pid: str):
        """Tell ComfyUI to interrupt the running job and remove it from the queue."""
        try:
            requests.post(f"{comfy_url}/interrupt", timeout=3)
        except Exception:
            pass
        try:
            requests.post(f"{comfy_url}/queue", json={"delete": [pid]}, timeout=3)
        except Exception:
            pass

    try:
        res = requests.post(f"{comfy_url}/prompt", json={"prompt": populated_workflow}, timeout=5.0)
        if res.status_code != 200:
            try:
                err_data = res.json()
                formatted_err = format_comfy_validation_error(err_data)
                if formatted_err:
                    raise Exception(formatted_err)
            except Exception as e_inner:
                if "Missing" in str(e_inner):
                    raise e_inner
            raise Exception(f"ComfyUI server returned status code {res.status_code}")
        
        prompt_id = res.json().get("prompt_id")
        if not prompt_id:
            raise Exception("Did not receive a prompt ID from ComfyUI")

        # Poll history endpoint for output
        from runners.runners import cancelled_sessions
        for _ in range(300):
            # Honour session cancellation — stop polling and kill the ComfyUI job
            if session_id and session_id in cancelled_sessions:
                _cancel_comfy_job(prompt_id)
                return "Error: Image generation cancelled by user."

            history_res = requests.get(f"{comfy_url}/history/{prompt_id}", timeout=10)
            if history_res.status_code == 200:
                history_data = history_res.json()
                if prompt_id in history_data:
                    outputs = history_data[prompt_id].get("outputs", {})
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for img in node_output["images"]:
                                filename = img["filename"]
                                view_res = requests.get(f"{comfy_url}/view", params={
                                    "filename": filename,
                                    "subfolder": img.get("subfolder", ""),
                                    "type": img.get("type", "temp")
                                }, timeout=15)
                                
                                if view_res.status_code == 200:
                                    parent_dir = os.path.dirname(save_path)
                                    if parent_dir:
                                        os.makedirs(parent_dir, exist_ok=True)
                                    with open(save_path, "wb") as img_file:
                                        img_file.write(view_res.content)
                                    
                                    # Delete the file from ComfyUI's folder to avoid accumulation
                                    try:
                                        from adapters.comfy_manager import COMFYUI_DIR
                                        img_type = img.get("type", "temp")
                                        comfy_file = os.path.normpath(os.path.join(COMFYUI_DIR, img_type, img.get("subfolder", ""), filename))
                                        if os.path.exists(comfy_file):
                                            os.remove(comfy_file)
                                            print(f"[COMFY IMAGE] Cleaned up {img_type} output image: {comfy_file}")
                                    except Exception as e_clean:
                                        print(f"[COMFY IMAGE] Warning: Failed to clean up file: {e_clean}")
                                        
                                    return save_path
                                else:
                                    raise Exception(f"Error downloading image: status {view_res.status_code}")
            time.sleep(1)
        raise Exception("Image generation timed out on ComfyUI server after 300 seconds.")
    except Exception as e:
        return f"Error executing ComfyUI workflow: {e}"
@track_tool_activity
def generate_local_image(prompt: str, subject_type: str = "auto") -> str:
    """Generates a local image using the in-process GPU diffusion engine.
    
    Args:
        prompt: A prompt describing what you are doing or the scene/expression.
        subject_type: "follower", "player", "environment", or "auto" (detected from prompt)
        
    Returns:
        A markdown link to the generated image, or an error message.
    """
    import os
    import random
    import time
    import json

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from runners.follower import get_active_follower
    active_follower = get_active_follower()

    prompt_lower = prompt.lower()
    if subject_type == "auto":
        if any(w in prompt_lower for w in ("scenery", "environment", "landscape", "no humans", "no characters", "dungeon corridor", "exterior", "architectural")):
            mode = "environment"
        elif any(w in prompt_lower for w in ("player character", "player portrait", "the hero", "adventurer", "named ")) and not any(w in prompt_lower for w in ("ria silmane", "spectral", "ghost woman")):
            mode = "player"
        else:
            mode = "follower"
    else:
        mode = subject_type

    img_details_val = ""
    neg_details_val = ""

    if mode == "player":
        try:
            from core.character import load_character
            from runners.follower import get_active_user
            sheet = load_character(get_active_user())
            race = sheet.get("race", "Nord")
            gender = sheet.get("gender", "Male")
            char_class = sheet.get("class", "Warrior")
            img_details_val = f"Elder Scrolls fantasy character art, {gender} {race} {char_class}, portrait, highly detailed, dramatic lighting"
            neg_details_val = "worst quality, low quality, deformed, mutated, extra limbs, watermark, text, modern clothing, contemporary"
        except Exception as pe:
            print(f"[DEBUG] Error reading player details for image generation: {pe}", flush=True)
            img_details_val = "Elder Scrolls fantasy character art, portrait, highly detailed, dramatic lighting"
            neg_details_val = "worst quality, low quality, deformed, mutated, extra limbs, watermark, text"
    elif mode == "environment":
        try:
            from core.world_engine import load_world_state
            from runners.follower import get_active_user
            world = load_world_state(get_active_user())
            loc = world.get("current_location", "Imperial Dungeon")
            prov = world.get("current_province", "Cyrodiil")
            img_details_val = f"scenery, environment landscape art, {loc}, {prov}, Elder Scrolls aesthetic, atmospheric lighting, detailed architecture, empty, no humans, no people"
            neg_details_val = "worst quality, low quality, character, human, person, 1girl, 1boy, face, portrait, deformed, watermark, text"
        except Exception as ee:
            print(f"[DEBUG] Error reading environment details for image generation: {ee}", flush=True)
            img_details_val = "scenery, environment landscape art, Elder Scrolls aesthetic, atmospheric lighting, detailed architecture, empty, no humans, no people"
            neg_details_val = "worst quality, low quality, character, human, person, 1girl, 1boy, face, portrait, deformed, watermark, text"
    else:
        # Follower mode: Load image prompt tags from active follower profile
        follower_json_path = os.path.normpath(os.path.join(
            base_dir, "core", "followers", active_follower, f"{active_follower}.json"
        ))
        if os.path.exists(follower_json_path):
            try:
                with open(follower_json_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                card = raw.get("data", raw)
                arena_ext = card.get("extensions", {}).get("arena", {})
                img_details = arena_ext.get("image_details", {})
                img_details_val = img_details.get("positive", "")
                neg_details_val = img_details.get("negative", "")
            except Exception as e:
                print(f"[DEBUG] Error reading active follower JSON for image generation: {e}", flush=True)

    # Combine prompt and image details
    from core.follower_config import replace_placeholders
    final_prompt = replace_placeholders(prompt)
    if img_details_val:
        if final_prompt and not final_prompt.endswith(","):
            final_prompt += ", "
        final_prompt += img_details_val
        
    final_negative = neg_details_val if neg_details_val else "worst quality, low quality, deformed, mutated, extra limbs, watermark, text"

    timestamp = int(time.time())
    local_filename = f"portrait_{timestamp}.png"
    portraits_dir = os.path.normpath(os.path.join(base_dir, "core", "followers", active_follower, "portraits"))
    local_path = os.path.join(portraits_dir, local_filename)
    os.makedirs(portraits_dir, exist_ok=True)

    # Execute in-process DirectML GPU diffusion engine
    try:
        from adapters.vram_orchestrator import start_img
        start_img()

        from core.engine_diffusion import generate_portrait_image
        generate_portrait_image(
            prompt=final_prompt,
            negative_prompt=final_negative,
            save_path=local_path
        )
        json_path = os.path.join(portraits_dir, f"portrait_{timestamp}.json")
        try:
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump({"prompt": prompt, "full_prompt": final_prompt, "mode": mode, "engine": "in_process_gpu"}, jf, indent=4)
        except Exception:
            pass
        return f"![Portrait](/images/portraits/{local_filename}?v={timestamp})"
    except Exception as e:
        print(f"[engine_diffusion] Error generating image: {e}")
        return f"Error generating portrait: {e}"


@track_tool_activity
def generate_follower_portrait(prompt: str) -> str:
    """Generates a portrait of the active companion."""
    return generate_local_image(prompt, subject_type="follower")


@track_tool_activity
def generate_player_portrait(prompt: str) -> str:
    """Generates a portrait of the player character based on character sheet and profile."""
    return generate_local_image(prompt, subject_type="player")


@track_tool_activity
def generate_environment_image(prompt: str) -> str:
    """Generates an atmospheric scene depiction of the current environment and location."""
    return generate_local_image(prompt, subject_type="environment")



@track_tool_activity

def generate_video_from_image(image_path: str, prompt: str) -> str:
    """Animates a local image using ComfyUI with a custom video-specific workflow template.
    
    Args:
        image_path: Absolute path to the source static image.
        prompt: Prompt describing the animation/motion.
        
    Returns:
        Public web serving path/URL to the generated video, or raises an Exception.
    """
    import os
    import time
    import json
    import random
    import shutil
    import requests
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    from runners.follower import get_active_follower as get_active_program
    active_program = get_active_program()
    
    workflow_env_path = os.getenv("COMFYUI_VIDEO_WORKFLOW", "core/skills/portrait_generation/VideoWorkflow.json")
    workflow_path = os.path.normpath(os.path.join(base_dir, workflow_env_path))
    
    if not os.path.exists(workflow_path):
        raise Exception(f"Video workflow template not found at '{workflow_path}'")
        
    if not os.path.exists(image_path):
        raise Exception(f"Source image not found at '{image_path}'")
        
    # Copy and resize source image to ComfyUI's input directory using PIL
    from variables.settings import COMFYUI_SERVER_URL
    from adapters.comfy_manager import COMFYUI_DIR
    from PIL import Image
    comfy_input_dir = os.path.normpath(os.path.join(COMFYUI_DIR, "input"))
    os.makedirs(comfy_input_dir, exist_ok=True)
    
    # Generate unique filename to avoid collision in ComfyUI input directory
    source_filename = os.path.basename(image_path)
    timestamp = int(time.time())
    unique_input_filename = f"anim_in_{timestamp}_{source_filename}"
    comfy_input_path = os.path.join(comfy_input_dir, unique_input_filename)
    
    # Determine dimensions maintaining aspect ratio, maximum 768, rounded to multiples of 32
    with Image.open(image_path) as img:
        orig_w, orig_h = img.size
    
    max_dim = 768
    if orig_w > orig_h:
        new_w = max_dim
        new_h = int(orig_h * (max_dim / orig_w))
    else:
        new_h = max_dim
        new_w = int(orig_w * (max_dim / orig_h))
        
    # Align to nearest multiple of 32 (works universally for both SDXL/AnimateDiff and LTX 2.3/Hunyuan/Flux)
    new_w = max(32, (new_w // 32) * 32)
    new_h = max(32, (new_h // 32) * 32)
    
    print(f"[COMFY VIDEO] Resizing source image from {orig_w}x{orig_h} to {new_w}x{new_h} and saving to {comfy_input_path}")
    with Image.open(image_path) as img:
        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        resized_img.save(comfy_input_path)
    
    # Define replacements for the workflow JSON
    seed_val = random.randint(1, 2147483647)
    replacements = {
        "%input_image%": unique_input_filename,
        "%prompt%": prompt,
        "%seed%": seed_val,
        "%width%": new_w,
        "%height%": new_h
    }
    
    # Load and populate workflow JSON
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow_data = json.load(f)
        
    def replace_val(obj):
        if isinstance(obj, dict):
            return {k: replace_val(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_val(x) for x in obj]
        elif isinstance(obj, str):
            has_placeholder = any(k in obj for k in replacements)
            for k, v in replacements.items():
                if k in obj:
                    obj = obj.replace(k, str(v))
            # Try to cast numeric placeholders only if it was a placeholder
            if has_placeholder:
                if obj.isdigit():
                    return int(obj)
                try:
                    return float(obj)
                except ValueError:
                    pass
            return obj
        return obj

    populated_workflow = replace_val(workflow_data)
    import json
    
    # Ensure ComfyUI server is running
    from adapters.comfy_manager import check_comfy_running
    if not check_comfy_running(force_refresh=True):
        raise Exception("ComfyUI server is offline. Please start the ComfyUI engine manually from the settings panel.")
            
    # Run dependency resolution inline to ensure missing custom nodes or models are downloaded/installed
    from adapters.comfy_manager import _resolver_worker, resolution_status
    print("[COMFY VIDEO] Checking and resolving workflow dependencies inline...")
    _resolver_worker(json.dumps(populated_workflow))
    if resolution_status.get("status") == "failed":
        print(f"[COMFY VIDEO] Dependency resolution failed: {resolution_status.get('progress')}")
        raise Exception(f"Failed to resolve workflow dependencies: {resolution_status.get('progress')}")
    print("[COMFY VIDEO] Dependency resolution completed successfully.")
    
    # Wait for ComfyUI to come back online if it was restarted
    print("[COMFY VIDEO] Waiting for ComfyUI server to be responsive...")
    for _ in range(60): # up to 60 seconds
        if check_comfy_running(force_refresh=True):
            break
        time.sleep(1)
        
    print(f"[COMFY VIDEO] Populated workflow JSON:\n{json.dumps(populated_workflow, indent=2)}")
    
    comfy_url = COMFYUI_SERVER_URL
    print(f"[COMFY VIDEO] Submitting workflow to ComfyUI server: {comfy_url}")
    
    res = requests.post(f"{comfy_url}/prompt", json={"prompt": populated_workflow}, timeout=10.0)
    if res.status_code != 200:
        # Try to clean up input image
        try:
            os.remove(comfy_input_path)
        except Exception:
            pass
        print(f"[COMFY VIDEO] Validation error response (HTTP {res.status_code}): {res.text}")
        try:
            err_data = res.json()
            formatted_err = format_comfy_validation_error(err_data)
            if formatted_err:
                raise Exception(formatted_err)
        except Exception as e_inner:
            if "Missing" in str(e_inner) or "Validation Error" in str(e_inner):
                raise e_inner
        raise Exception(f"ComfyUI server prompt execution failed with status {res.status_code}")

        
    prompt_id = res.json().get("prompt_id")
    if not prompt_id:
        try:
            os.remove(comfy_input_path)
        except Exception:
            pass
        raise Exception("ComfyUI server did not return a prompt_id")
        
    # Poll for completion
    completed_filename = None
    output_key = None
    file_info = None
    start_time = time.time()
    try:
        # Give it up to 1800 seconds (30 minutes) for slow/high-res generations
        for _ in range(900):
            history_res = requests.get(f"{comfy_url}/history/{prompt_id}", timeout=10)
            if history_res.status_code == 200:
                history_data = history_res.json()
                if prompt_id in history_data:
                    prompt_info = history_data[prompt_id]
                    outputs = prompt_info.get("outputs", {})
                    
                    # 1. Try to find standard media in the outputs
                    for node_id, node_output in outputs.items():
                        for possible_key in ["images", "gifs", "videos"]:
                            if possible_key in node_output and node_output[possible_key]:
                                file_info = node_output[possible_key][0]
                                completed_filename = file_info["filename"]
                                output_key = possible_key
                                break
                        if completed_filename:
                            break
                            
                    # 2. If no output media found in outputs, scan ComfyUI temp folder for civitai videos
                    if not completed_filename:
                        from adapters.comfy_manager import COMFYUI_DIR
                        temp_dir = os.path.normpath(os.path.join(COMFYUI_DIR, "temp"))
                        if os.path.exists(temp_dir):
                            newest_file = None
                            newest_time = 0
                            # Look for files matching civitai_*.mp4, civitai_*.webm, civitai_*.gif
                            for f_name in os.listdir(temp_dir):
                                if f_name.startswith("civitai_") and f_name.lower().endswith((".mp4", ".webm", ".gif")):
                                    f_path = os.path.join(temp_dir, f_name)
                                    mtime = os.path.getmtime(f_path)
                                    # Must be created after we started (with a buffer for clock drift)
                                    if mtime >= start_time - 10:
                                        if mtime > newest_time:
                                            newest_time = mtime
                                            newest_file = f_name
                            if newest_file:
                                completed_filename = newest_file
                                output_key = "videos"
                                file_info = {
                                    "filename": completed_filename,
                                    "subfolder": "",
                                    "type": "temp"
                                }
                                print(f"[COMFY VIDEO] Found newly generated Civitai temp video: {completed_filename}")
                                
                    if completed_filename:
                        break
                    else:
                        status_info = prompt_info.get("status", {})
                        status_str = status_info.get("status_str", "unknown")
                        raise Exception(f"ComfyUI prompt execution finished (status: {status_str}), but no output video file could be resolved.")
            time.sleep(2)
            
        if not completed_filename:
            raise Exception("Video generation timed out on ComfyUI server.")
            
        # Download the generated media file
        print(f"[COMFY VIDEO] Downloading generated file: {completed_filename} (type: {output_key})")
        view_res = requests.get(f"{comfy_url}/view", params={
            "filename": completed_filename,
            "subfolder": file_info.get("subfolder", ""),
            "type": file_info.get("type", "output")
        }, timeout=30)
        
        if view_res.status_code != 200:
            raise Exception(f"Failed to download generated file from ComfyUI: HTTP {view_res.status_code}")
            
        # Determine the correct file extension from the downloaded filename
        _, ext = os.path.splitext(completed_filename)
        if not ext:
            ext = ".mp4"  # Default fallback
            
        # Determine save path: next to the original portrait/image
        source_dir = os.path.dirname(image_path)
        source_base, _ = os.path.splitext(source_filename)
        output_filename = f"{source_base}{ext}"
        save_path = os.path.join(source_dir, output_filename)
        
        print(f"[COMFY VIDEO] Saving output video/animated media to {save_path}")
        with open(save_path, "wb") as out_file:
            out_file.write(view_res.content)
            
        # Delete temp file from ComfyUI's temp/output folder to avoid accumulation
        try:
            folder_type = file_info.get("type", "output")
            folder_name = "temp" if folder_type == "temp" else "output"
            comfy_temp_file = os.path.normpath(os.path.join(COMFYUI_DIR, folder_name, file_info.get("subfolder", ""), completed_filename))
            if os.path.exists(comfy_temp_file):
                os.remove(comfy_temp_file)
                print(f"[COMFY VIDEO] Cleaned up temp output video: {comfy_temp_file}")
        except Exception as e_clean:
            print(f"[COMFY VIDEO] Warning: Failed to clean up temp file: {e_clean}")
            
        # Get relative public path
        # E.g. core/followers/ria_silmane/portraits/portrait_123.mp4 -> /images/portraits/portrait_123.mp4
        normalized_path = os.path.normpath(save_path)
        parts = normalized_path.split(os.sep)
        try:
            fol_idx = parts.index("followers")
            rel_parts = parts[fol_idx + 2:]
            url_path = "/images/" + "/".join(rel_parts)
        except ValueError:
            url_path = f"/images/portraits/{output_filename}"
            
        return url_path
        
    finally:
        # Clean up temporary input file from ComfyUI's input directory
        try:
            if os.path.exists(comfy_input_path):
                os.remove(comfy_input_path)
        except Exception as e:
            print(f"[COMFY VIDEO] Warning: Failed to delete temp input image {comfy_input_path}: {e}")





@track_tool_activity
def add_quest(title: str, notes: str, due: str = None, location: str = "", reminder_minutes: int = 15) -> str:
    """Creates a new staged side quest and adds it to the user's quest log."""
    try:
        from core.side_quests import create_side_quest
        res = create_side_quest(title=title, notes=notes, due=due, location=location, reminder_minutes=reminder_minutes)
        return res.get("message", f"Added side quest '{title}'")
    except Exception as e:
        return f"Error adding quest: {e}"

@track_tool_activity
def arena_add_side_quest(title: str, notes: str, due: str = None, location: str = "", reminder_minutes: int = 15) -> str:
    """Creates a new staged side quest with sequential objectives."""
    return add_quest(title=title, notes=notes, due=due, location=location, reminder_minutes=reminder_minutes)

@track_tool_activity
def arena_advance_side_quest(quest_id: str = None, *args, **kwargs) -> dict:
    """Advances an active side quest to its next sequential stage or marks it completed."""
    from core.side_quests import advance_side_quest
    qid = quest_id or kwargs.get("id") or (args[0] if args and isinstance(args[0], str) else None)
    return advance_side_quest(quest_id=qid)

@track_tool_activity
def arena_complete_side_quest(quest_id: str = None, *args, **kwargs) -> dict:
    """Directly completes and archives an active side quest."""
    from core.side_quests import complete_side_quest
    qid = quest_id or kwargs.get("id") or (args[0] if args and isinstance(args[0], str) else None)
    return complete_side_quest(quest_id=qid)


@track_tool_activity
def add_journal_entry(keyphrases: str, content: str) -> str:
    """Saves a memory journal entry for the active program.
    
    Args:
        keyphrases: Comma separated keywords or phrases that trigger this memory.
        content: The specific, important detail or memory to record (up to 300 characters).
    """
    try:
        from core.journals import add_journal_entry as add_entry
        from runners.follower import get_active_follower as get_active_program
        active_prog = get_active_program()
        entry = add_entry(keyphrases, content, active_prog)
        return f"Successfully saved memory journal entry: {entry.get('content')}"
    except Exception as e:
        return f"Error saving memory journal entry: {e}"

# --- Arena Additions ---

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.mechanics import roll_check, roll_combat, roll_initiative, roll_skill, sorcerer_absorb, request_skill_check
from core.world_engine import load_world_state, save_world_state, get_location_context, travel, advance_time, set_flag, discover_location, set_location
from core.quest_tracker import load_quest_stages, get_stage_context_injection, check_stage_conditions, advance_stage, advance_quest_stage
from core.spellmaker import evaluate_spell, get_school_for_effect

@track_tool_activity
def arena_request_skill_check(skill_name: str, attribute_name: str, dc: int, reason: str = ""):
    """Request an interactive skill or attribute check from the player character when the narrative requires active player reaction. Triggers player dice roll."""
    return request_skill_check(skill_name, attribute_name, dc, reason)

@track_tool_activity
def arena_roll_check(attribute_name, attribute_value, dc, advantage=False, disadvantage=False):
    """Roll a d20 attribute check for the current scene. Results appear as a collapsible tool call. The LLM narrates only the outcome, never the numbers."""
    return roll_check(attribute_name, attribute_value, dc, advantage, disadvantage)


@track_tool_activity
def arena_roll_combat(
    attacker_name="Attacker",
    target_name="{{user}}",
    weapon_name="Attack",
    attacker_strength=None,
    attacker_agility=None,
    attacker_class_archetype="Warrior",
    weapon_damage_tier=1,
    weapon_attribute="strength",
    target_agility=None,
    **kwargs
):
    """Resolve a combat attack roll between an attacker and target."""
    from core.mechanics import get_monster, roll_combat

    save_id, sheet = _get_active_sheet(kwargs)

    # Resolve monster stats if attacker is in bestiary
    monster = get_monster(attacker_name) if attacker_name else {}
    str_val = attacker_strength if attacker_strength is not None else monster.get("strength", 50)
    agi_val = attacker_agility if attacker_agility is not None else monster.get("agility", 50)

    # Resolve target agility
    is_target_player = str(target_name).lower() in ("{{user}}", "player", "hero", sheet.get("name", "").lower(), "eternal champion")
    if target_agility is None:
        if is_target_player:
            target_agility = sheet.get("agility", 50)
        else:
            target_monster = get_monster(target_name)
            target_agility = target_monster.get("agility", 50)

    attacker = {
        "name": attacker_name,
        "strength": int(str_val),
        "agility": int(agi_val),
        "class_archetype": attacker_class_archetype
    }
    target = {
        "name": target_name,
        "agility": int(target_agility),
        "is_player": is_target_player
    }
    weapon = {
        "name": weapon_name,
        "damage_tier": int(weapon_damage_tier or 1),
        "attribute": weapon_attribute,
        "attribute_used": weapon_attribute
    }
    return roll_combat(attacker, weapon, target)

@track_tool_activity
def arena_roll_initiative(combatants_json):
    """Roll initiative for all combatants in a combat encounter."""
    import json
    combatants = json.loads(combatants_json)
    return roll_initiative(combatants)

@track_tool_activity
def arena_roll_skill(skill_name, attribute_name, attribute_value, dc):
    """Roll a skill check (lockpicking, stealth, persuasion, etc.) using the d20 narrative system."""
    return roll_skill(skill_name, attribute_name, attribute_value, dc)

@track_tool_activity
def arena_sorcerer_absorb(intelligence, willpower, incoming_spell_tier):
    """Check if a Sorcerer's passive Spell Absorption activates against an incoming spell."""
    return sorcerer_absorb(intelligence, willpower, incoming_spell_tier)

@track_tool_activity
def arena_get_location(**kwargs):
    """Get the current location context for the active character."""
    import json
    world_state = load_world_state()
    with open(os.path.join(os.path.dirname(__file__), "core", "world", "provinces.json"), "r", encoding="utf-8") as f:
        provinces = json.load(f)
    dungeons_path = os.path.join(os.path.dirname(__file__), "core", "world", "dungeons.json")
    dungeons = []
    if os.path.exists(dungeons_path):
        with open(dungeons_path, "r", encoding="utf-8") as f:
            dungeons = json.load(f)
    return get_location_context(world_state, provinces, [], dungeons)

@track_tool_activity
def arena_set_location(province, location_name, advance_hours=0, **kwargs):
    """Directly sets the character's active location and province (e.g. exiting a shift gate, entering a dungeon or city)."""
    return set_location(province, location_name, advance_hours)

@track_tool_activity
def arena_travel(destination_province, destination_city, **kwargs):
    """Travel to a new province and city. Updates world state and advances time."""
    world_state = load_world_state()
    world_state, travel_summary = travel(world_state, destination_province, destination_city)
    save_world_state(world_state)
    return travel_summary

@track_tool_activity
def arena_advance_stage(quest_id=None, *args, **kwargs):
    """Advances the main quest or a specified side quest to the next sequential stage."""
    qid = quest_id or kwargs.get("id") or (args[0] if args and isinstance(args[0], str) and (args[0].startswith("sq_") or args[0].startswith("quest_")) else None)
    if qid and (str(qid).startswith("sq_") or str(qid).startswith("quest_") or "side" in kwargs):
        from core.side_quests import advance_side_quest
        return advance_side_quest(quest_id=str(qid))
    return advance_quest_stage()

@track_tool_activity
def arena_set_quest_stage(stage_number=None, *args, **kwargs):
    """Directly sets the main quest stage number for the character."""
    stage = stage_number or kwargs.get("stage") or kwargs.get("target_stage") or kwargs.get("next_stage") or kwargs.get("new_stage")
    if stage is not None:
        try:
            stage = int(stage)
        except (ValueError, TypeError):
            stage = None
    return advance_quest_stage(target_stage=stage)

@track_tool_activity
def arena_recruit_follower(follower_name, follower_race="Imperial", follower_class="Adventurer", persona_description=""):
    """Recruit an NPC into your party as an active follower when they agree to join or follow you narratively."""
    try:
        import os, re, time, json
        from variables.settings import BASE_DIR, FOLLOWERS_DIR
        follower_id = re.sub(r'[^a-zA-Z0-9_\-]', '', follower_name).lower()
        if not follower_id:
            follower_id = f"follower_{int(time.time())}"
            
        follower_path = os.path.join(FOLLOWERS_DIR, follower_id)
        if not os.path.exists(follower_path):
            os.makedirs(follower_path, exist_ok=True)
            desc = persona_description or f"A loyal {follower_race} {follower_class} following the Eternal Champion into combat."
            profile_data = {
                "name": follower_name,
                "operation": {
                    "description": desc,
                    "personality": "Loyal, vigilant",
                    "scenario": f"Traveling alongside {{user}} through Tamriel as a {follower_race} companion."
                }
            }
            json_path = os.path.join(program_path, f"{program_id}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
                
        return {"status": "recruited", "follower_name": follower_name, "race": follower_race, "class": follower_class}
    except Exception as e:
        return {"status": "recruited", "follower_name": follower_name, "message": str(e)}

# ── Character sheet tools ─────────────────────────────────────────────────────
import os
from core.save_manager import get_active_save_id
from core.character import (
    load_character, save_character, get_character_context,
    take_damage, heal, spend_magicka, restore_magicka, spend_stamina, restore_stamina, rest,
    spend_spell_points, restore_spell_points,
    add_gold, spend_gold, add_item, remove_item, equip_item,
    learn_spell, add_effect, remove_effect, add_condition, remove_condition,
    add_experience, get_attribute, is_dead, tick_effects
)

def _get_active_sheet(kwargs: dict = None) -> tuple[str, dict]:
    """Helper to fetch active save_id and load the corresponding sheet."""
    save_id = get_active_save_id()
    sheet = load_character(save_id)
    return save_id, sheet

def _commit_and_sync(save_id: str, sheet: dict, kwargs: dict = None):
    """Helper to persist updated character sheet to active save."""
    save_character(sheet, save_id)

@track_tool_activity
def arena_take_damage(amount=0, damage_amount=None, damage=None, **kwargs):
    """Apply damage to the character. Updates HP on the character sheet."""
    actual_amount = amount if amount else (damage_amount if damage_amount is not None else (damage if damage is not None else 0))
    inc_mult = float(os.getenv("INCOMING_DAMAGE_MULTIPLIER", "1.0"))
    scaled_amount = max(1, int(round(int(actual_amount) * inc_mult))) if int(actual_amount) > 0 else 0
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet = take_damage(sheet, scaled_amount)
    _commit_and_sync(save_id, sheet, kwargs)
    
    d = sheet["derived"]
    return {"hp_current": d["hp_current"], "hp_max": d["hp_max"], "dead": is_dead(sheet), "damage_inflicted": scaled_amount}

@track_tool_activity
def arena_heal(amount=0, heal_amount=None, healing=None, **kwargs):
    """Restore HP to the character up to their maximum."""
    actual_amount = amount if amount else (heal_amount if heal_amount is not None else (healing if healing is not None else 0))
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet = heal(sheet, int(actual_amount))
    _commit_and_sync(save_id, sheet, kwargs)
    
    d = sheet["derived"]
    return {"hp_current": d["hp_current"], "hp_max": d["hp_max"]}

@track_tool_activity
def arena_spend_magicka(amount=0, mp_amount=None, cost=None, **kwargs):
    """Spend Magicka (MP) to cast a spell. Returns success or failure if MP insufficient."""
    actual_amount = amount if amount else (mp_amount if mp_amount is not None else (cost if cost is not None else 0))
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet, success = spend_magicka(sheet, int(actual_amount))
    if success:
        _commit_and_sync(save_id, sheet, kwargs)
        
    d = sheet["derived"]
    return {"success": success, "mp_current": d.get("mp_current", 0), "mp_max": d.get("mp_max", 42)}

@track_tool_activity
def arena_spend_spell_points(amount=0, **kwargs):
    """Backwards compatibility alias for arena_spend_magicka."""
    return arena_spend_magicka(amount=amount, **kwargs)

@track_tool_activity
def arena_restore_magicka(amount=0, mp_amount=None, **kwargs):
    """Restore Magicka (MP) up to maximum (via potions, absorbing spells, or rest)."""
    actual_amount = amount if amount else (mp_amount if mp_amount is not None else 0)
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet = restore_magicka(sheet, int(actual_amount))
    _commit_and_sync(save_id, sheet, kwargs)
    
    d = sheet["derived"]
    return {"mp_current": d.get("mp_current", 0), "mp_max": d.get("mp_max", 42)}

@track_tool_activity
def arena_spend_stamina(amount=0, stamina_amount=None, cost=None, **kwargs):
    """Spend Stamina for sprinting, heavy power strikes, dodging, or physical exertion."""
    actual_amount = amount if amount else (stamina_amount if stamina_amount is not None else (cost if cost is not None else 0))
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet, not_exhausted = spend_stamina(sheet, int(actual_amount))
    _commit_and_sync(save_id, sheet, kwargs)
    
    d = sheet["derived"]
    return {"stamina_current": d.get("stamina_current", 0), "stamina_max": d.get("stamina_max", 50), "exhausted": not not_exhausted}

@track_tool_activity
def arena_restore_stamina(amount=0, stamina_amount=None, **kwargs):
    """Restore Stamina up to maximum (potions, resting, catching breath)."""
    actual_amount = amount if amount else (stamina_amount if stamina_amount is not None else 0)
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet = restore_stamina(sheet, int(actual_amount))
    _commit_and_sync(save_id, sheet, kwargs)
    
    d = sheet["derived"]
    return {"stamina_current": d.get("stamina_current", 0), "stamina_max": d.get("stamina_max", 50)}

@track_tool_activity
def arena_rest(hours=8, safe=True, **kwargs):
    """Rest or sleep at an inn or camp to recover Health, Stamina, and Magicka."""
    save_id, sheet = _get_active_sheet(kwargs)
    d = sheet["derived"]
    hp_before = d.get("hp_current", 0)
    mp_before = d.get("mp_current", 0)
    stamina_before = d.get("stamina_current", 0)
    
    sheet, summary = rest(sheet, int(hours), bool(safe))
    _commit_and_sync(save_id, sheet, kwargs)
    
    d = sheet["derived"]
    return {
        "summary": summary,
        "hp_current": d.get("hp_current", 28),
        "hp_max": d.get("hp_max", 28),
        "mp_current": d.get("mp_current", 42),
        "mp_max": d.get("mp_max", 42),
        "stamina_current": d.get("stamina_current", 50),
        "stamina_max": d.get("stamina_max", 50),
        "hp_before": hp_before,
        "mp_before": mp_before,
        "stamina_before": stamina_before
    }

@track_tool_activity
def arena_add_gold(amount=0, gold_amount=None, **kwargs):
    """Add gold to the character (loot, reward, sale)."""
    actual_amount = amount if amount else (gold_amount if gold_amount is not None else 0)
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet = add_gold(sheet, int(actual_amount))
    _commit_and_sync(save_id, sheet, kwargs)
    
    return {"gold": sheet["gold"]}

@track_tool_activity
def arena_spend_gold(amount=0, gold_amount=None, cost=None, **kwargs):
    """Spend gold on a purchase. Returns success or failure if funds insufficient."""
    actual_amount = amount if amount else (gold_amount if gold_amount is not None else (cost if cost is not None else 0))
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet, success = spend_gold(sheet, int(actual_amount))
    if success:
        _commit_and_sync(save_id, sheet, kwargs)
        
    return {"success": success, "gold": sheet["gold"]}

@track_tool_activity
def arena_add_item(item_name, item_type="Item", quantity=1, weight=None, **kwargs):
    """Add an item to the character's inventory (looted, purchased, found)."""
    save_id, sheet = _get_active_sheet(kwargs)
    item_dict = {
        "name": str(item_name).strip(),
        "type": str(item_type).strip(),
        "quantity": int(quantity)
    }
    if weight is not None:
        try:
            item_dict["weight"] = float(weight)
        except (ValueError, TypeError):
            pass
            
    sheet = add_item(sheet, item_dict)
    _commit_and_sync(save_id, sheet, kwargs)
    
    return {"inventory_count": len(sheet["inventory"]), "item": item_name}

@track_tool_activity
def arena_remove_item(item_name, quantity=1, **kwargs):
    """Remove an item from inventory (used, sold, consumed)."""
    save_id, sheet = _get_active_sheet(kwargs)
    sheet, success = remove_item(sheet, item_name, int(quantity))
    if success:
        _commit_and_sync(save_id, sheet, kwargs)
        
    return {"success": success, "item": item_name}

@track_tool_activity
def arena_create_spell(spell_name, effect_description, school=None, target_type="Target", tier=2, deduct_gold=True, **kwargs):
    """
    Craft and inscribe a new custom spell at a Mages Guild or through arcane study.
    Calculates Magicka cost (SP), casting DC, and inscribers' fee.
    """
    from core.spellmaker import create_spell as craft_spell
    save_id, sheet = _get_active_sheet(kwargs)
    caster_int = sheet.get("intelligence", 50)
    
    spell_info = craft_spell(
        name=spell_name,
        effect_description=effect_description,
        school=school,
        target_type=target_type,
        tier=int(tier),
        caster_intelligence=caster_int
    )
    
    gold_fee = spell_info["gold_fee"]
    current_gold = sheet.get("gold", 0)
    
    if deduct_gold and current_gold < gold_fee:
        return {
            "success": False,
            "error": f"Insufficient gold. Creating '{spell_name}' requires {gold_fee} gold, but you only have {current_gold} gold.",
            "spell_info": spell_info
        }
        
    if deduct_gold:
        sheet["gold"] = max(0, current_gold - gold_fee)
        
    # Learn the crafted spell
    sheet = learn_spell(sheet, {
        "name": spell_info["name"],
        "school": spell_info["school"],
        "tier": spell_info["tier"],
        "sp_cost": spell_info["sp_cost"],
        "target_type": spell_info["target_type"],
        "effect_description": spell_info["effect_description"]
    })
    _commit_and_sync(save_id, sheet, kwargs)
    
    return {
        "success": True,
        "spell": spell_info,
        "gold_spent": gold_fee if deduct_gold else 0,
        "remaining_gold": sheet.get("gold", 0),
        "spells": [s["name"] for s in sheet.get("spells", [])]
    }

@track_tool_activity
def arena_learn_spell(spell_name, school="Restoration", tier=1, sp_cost=5, **kwargs):
    """Add a spell to the character's known spells."""
    save_id, sheet = _get_active_sheet(kwargs)
    sheet = learn_spell(sheet, {"name": spell_name, "school": school, "tier": tier, "sp_cost": sp_cost})
    _commit_and_sync(save_id, sheet, kwargs)
    
    return {"spells": [s["name"] for s in sheet["spells"]]}

@track_tool_activity
def arena_add_effect(effect_name, duration_turns=1, source="", **kwargs):
    """Apply a status effect to the character (poisoned, paralysed, fortified, etc.)."""
    save_id, sheet = _get_active_sheet(kwargs)
    sheet = add_effect(sheet, {"name": effect_name, "duration_turns": duration_turns, "source": source})
    _commit_and_sync(save_id, sheet, kwargs)
    
    return {"active_effects": [e["name"] for e in sheet["active_effects"]]}

@track_tool_activity
def arena_remove_effect(effect_name, **kwargs):
    """Remove a status effect (cured, expired, dispelled)."""
    save_id, sheet = _get_active_sheet(kwargs)
    sheet = remove_effect(sheet, effect_name)
    _commit_and_sync(save_id, sheet, kwargs)
    
    return {"active_effects": [e["name"] for e in sheet["active_effects"]]}

@track_tool_activity
def arena_add_experience(amount=0, xp_amount=None, **kwargs):
    """Award XP. Automatically handles level-up if threshold reached."""
    actual_amount = amount if amount else (xp_amount if xp_amount is not None else 0)
    
    save_id, sheet = _get_active_sheet(kwargs)
    sheet, leveled_up = add_experience(sheet, int(actual_amount))
    _commit_and_sync(save_id, sheet, kwargs)
    
    d = sheet.get("derived", {})
    return {
        "experience": sheet["experience"],
        "level": sheet["level"],
        "leveled_up": leveled_up,
        "hp_max": d.get("hp_max", 32),
        "mp_max": d.get("mp_max", 162)
    }

@track_tool_activity
def arena_get_character_context(**kwargs):
    """Return the current character sheet as a compact context string for the narrative."""
    _, sheet = _get_active_sheet(kwargs)
    return get_character_context(sheet)