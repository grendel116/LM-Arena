"""
core/engine_diffusion.py — Internal GPU-accelerated diffusion engine.

Executes SDXL image generation in-process with PyTorch/GPU acceleration,
using the exact parameters from ImageWorkflow.json.
"""

import os
import sys
import gc
import json
import time
import random
import threading
import subprocess
from typing import List, Dict, Any, Optional, Tuple

import torch
from variables.settings import CHECKPOINTS_DIR, LORAS_DIR, VAE_DIR, MODELS_DIR
from utils import lifecycle

_diffusion_lock = threading.Lock()
_active_checkpoint: Optional[str] = None
_COMFY_NODE_CACHE: Dict[Tuple[Any, ...], Any] = {}
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _persist_checkpoint_to_env(checkpoint_name: str) -> None:
    """Updates COMFYUI_CHECKPOINT in the .env configuration file."""
    try:
        env_file = os.path.join(root_dir, ".env")
        if not os.path.exists(env_file):
            return
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith("COMFYUI_CHECKPOINT="):
                lines[i] = f"COMFYUI_CHECKPOINT={checkpoint_name}\n"
                updated = True
                break
        if not updated:
            lines.append(f"\nCOMFYUI_CHECKPOINT={checkpoint_name}\n")
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"[engine_diffusion] Warning persisting checkpoint to .env: {e}")


def resolve_checkpoint_path(checkpoint_name: Optional[str] = None) -> str:
    """Resolves the absolute path to the requested, active, or configured checkpoint model."""
    if not checkpoint_name:
        checkpoint_name = _active_checkpoint or os.getenv("COMFYUI_CHECKPOINT")

    if checkpoint_name and os.path.isabs(checkpoint_name) and os.path.exists(checkpoint_name):
        return checkpoint_name

    candidates = []
    if checkpoint_name:
        candidates.append(os.path.join(CHECKPOINTS_DIR, checkpoint_name))
        candidates.append(os.path.join(MODELS_DIR, checkpoint_name))
        candidates.append(os.path.join(MODELS_DIR, "checkpoints", checkpoint_name))

    env_ckpt = os.getenv("COMFYUI_CHECKPOINT")
    if env_ckpt and env_ckpt != checkpoint_name:
        candidates.append(os.path.join(CHECKPOINTS_DIR, env_ckpt))
        candidates.append(os.path.join(MODELS_DIR, env_ckpt))

    for path in candidates:
        if os.path.exists(path):
            return path

    if os.path.exists(CHECKPOINTS_DIR):
        for f in os.listdir(CHECKPOINTS_DIR):
            if f.lower().endswith((".safetensors", ".ckpt")) and not f.startswith("."):
                return os.path.join(CHECKPOINTS_DIR, f)

    if os.path.exists(MODELS_DIR):
        for f in os.listdir(MODELS_DIR):
            if f.lower().endswith((".safetensors", ".ckpt")) and not f.startswith("."):
                return os.path.join(MODELS_DIR, f)

    raise FileNotFoundError(f"No checkpoint models found in {CHECKPOINTS_DIR} or {MODELS_DIR}.")


def resolve_checkpoint_name(checkpoint_name: Optional[str] = None) -> str:
    """Resolves the filename of the requested or default checkpoint model."""
    path = resolve_checkpoint_path(checkpoint_name)
    return os.path.basename(path)


def resolve_lora_path(lora_name: str) -> Optional[str]:
    """Resolves absolute path to a LoRA weights file."""
    if os.path.exists(lora_name):
        return lora_name

    candidates = [
        os.path.join(LORAS_DIR, lora_name),
        os.path.join(MODELS_DIR, "loras", lora_name),
        os.path.join(MODELS_DIR, lora_name)
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def list_checkpoints() -> List[Dict[str, Any]]:
    """Lists all available SafeTensors/checkpoint files in models/checkpoints."""
    ckpts = []
    seen = set()
    if os.path.exists(CHECKPOINTS_DIR):
        try:
            for root, _, files in os.walk(CHECKPOINTS_DIR):
                for f in files:
                    if f.lower().endswith((".safetensors", ".ckpt")) and not f.startswith("."):
                        full_path = os.path.join(root, f)
                        if full_path in seen:
                            continue
                        seen.add(full_path)
                        size_gb = round(os.path.getsize(full_path) / (1024 ** 3), 2)
                        ckpts.append({
                            "name": f,
                            "filename": f,
                            "path": full_path,
                            "size_gb": size_gb,
                            "folder": "checkpoints"
                        })
        except Exception as e:
            print(f"[engine_diffusion] Error scanning checkpoints in {CHECKPOINTS_DIR}: {e}")

    if os.path.exists(MODELS_DIR):
        try:
            for f in os.listdir(MODELS_DIR):
                full_path = os.path.join(MODELS_DIR, f)
                if os.path.isfile(full_path) and f.lower().endswith((".safetensors", ".ckpt")) and not f.startswith("."):
                    if full_path in seen:
                        continue
                    seen.add(full_path)
                    size_gb = round(os.path.getsize(full_path) / (1024 ** 3), 2)
                    ckpts.append({
                        "name": f,
                        "filename": f,
                        "path": full_path,
                        "size_gb": size_gb,
                        "folder": "models"
                    })
        except Exception as e:
            print(f"[engine_diffusion] Error scanning root MODELS_DIR: {e}")

    return sorted(ckpts, key=lambda x: x["name"])


def list_loras() -> List[Dict[str, Any]]:
    """Lists all available LoRAs in models/loras."""
    loras = []
    search_dirs = [LORAS_DIR, os.path.join(MODELS_DIR, "loras")]
    seen = set()
    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue
        try:
            for root, _, files in os.walk(s_dir):
                for f in files:
                    if f.lower().endswith((".safetensors", ".ckpt", ".pt")) and not f.startswith("."):
                        full_path = os.path.join(root, f)
                        if full_path in seen:
                            continue
                        seen.add(full_path)
                        size_mb = round(os.path.getsize(full_path) / (1024 ** 2), 1)
                        loras.append({
                            "name": f,
                            "filename": f,
                            "path": full_path,
                            "size_mb": size_mb,
                            "folder": os.path.relpath(root, MODELS_DIR)
                        })
        except Exception as e:
            print(f"[engine_diffusion] Error scanning LoRAs in {s_dir}: {e}")
    return sorted(loras, key=lambda x: x["name"])


def list_vaes() -> List[Dict[str, Any]]:
    """Lists all available VAE weights in models/vae."""
    vaes = []
    search_dirs = [VAE_DIR, os.path.join(MODELS_DIR, "vae")]
    seen = set()
    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue
        try:
            for root, _, files in os.walk(s_dir):
                for f in files:
                    if f.lower().endswith((".safetensors", ".pt", ".bin")) and not f.startswith("."):
                        full_path = os.path.join(root, f)
                        if full_path in seen:
                            continue
                        seen.add(full_path)
                        size_mb = round(os.path.getsize(full_path) / (1024 ** 2), 1)
                        vaes.append({
                            "name": f,
                            "filename": f,
                            "path": full_path,
                            "size_mb": size_mb,
                            "folder": os.path.relpath(root, MODELS_DIR)
                        })
        except Exception as e:
            print(f"[engine_diffusion] Error scanning VAEs in {s_dir}: {e}")
    return sorted(vaes, key=lambda x: x["name"])


def get_active_checkpoint() -> Optional[str]:
    """Returns the name of the currently selected checkpoint."""
    global _active_checkpoint
    if _active_checkpoint and os.path.exists(_active_checkpoint):
        return os.path.basename(_active_checkpoint)

    env_ckpt = os.getenv("COMFYUI_CHECKPOINT")
    if env_ckpt:
        try:
            resolved = resolve_checkpoint_path(env_ckpt)
            if resolved and os.path.exists(resolved):
                _active_checkpoint = resolved
                return os.path.basename(resolved)
        except Exception:
            pass

    ckpts = list_checkpoints()
    for c in ckpts:
        if "illustrious" in c["filename"].lower() or "sdxl" in c["filename"].lower():
            _active_checkpoint = c["path"]
            return c["filename"]
    if ckpts:
        _active_checkpoint = ckpts[0]["path"]
        return ckpts[0]["filename"]
    return None


def set_active_checkpoint(checkpoint_name: str) -> bool:
    """Sets the active diffusion checkpoint and persists it to environment and .env."""
    global _active_checkpoint, _COMFY_NODE_CACHE
    try:
        resolved = resolve_checkpoint_path(checkpoint_name)
        _active_checkpoint = resolved
        filename = os.path.basename(resolved)
        os.environ["COMFYUI_CHECKPOINT"] = filename

        # Clear cached checkpoint and dependent LoRAs/CLIP encodings if switched
        for key in list(_COMFY_NODE_CACHE.keys()):
            if key[0] in ("CheckpointLoaderSimple", "LoraLoader", "CLIPTextEncode"):
                del _COMFY_NODE_CACHE[key]

        _persist_checkpoint_to_env(filename)
        print(f"[engine_diffusion] Active checkpoint set to: {filename}")
        return True
    except Exception as e:
        print(f"[engine_diffusion] Failed to set active checkpoint: {e}")
        return False


DIFFUSION_SERVER_PORT = 8189
DIFFUSION_SERVER_URL = f"http://127.0.0.1:{DIFFUSION_SERVER_PORT}"
# Backward-compatibility aliases
DIFFUSION_DAEMON_PORT = DIFFUSION_SERVER_PORT
DIFFUSION_DAEMON_URL = DIFFUSION_SERVER_URL

_server_proc: Optional[subprocess.Popen] = None
_server_lock = threading.Lock()
_daemon_proc = None
_daemon_lock = _server_lock


def is_port_listening(port: int = DIFFUSION_SERVER_PORT) -> bool:
    """Checks if a TCP port is actively listening on localhost."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _cleanup_stale_port_process(port: int = DIFFUSION_SERVER_PORT) -> None:
    """Finds and terminates any orphaned process listening on the diffusion worker port."""
    if os.name != 'nt':
        return
    try:
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000
        output = subprocess.check_output("netstat -ano", shell=True, creationflags=flags).decode('utf-8', errors='ignore')
        for line in output.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = int(parts[-1])
                    if pid != os.getpid():
                        try:
                            import psutil
                            proc = psutil.Process(pid)
                            proc.kill()
                        except Exception:
                            subprocess.run(["taskkill", "/F", "/PID", str(pid)], creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def check_server_status() -> bool:
    """Checks if the diffusion server worker is online."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{DIFFUSION_SERVER_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


check_daemon_status = check_server_status


def ensure_server_running(timeout: float = 60.0) -> bool:
    """Starts the diffusion server worker if not already running."""
    global _server_proc, _daemon_proc
    if _server_proc is not None and _server_proc.poll() is None:
        return True

    if check_server_status():
        return True

    with _server_lock:
        if _server_proc is not None and _server_proc.poll() is None:
            return True

        if check_server_status():
            return True

        # Ensure no zombie process occupies the port before launching a new worker
        _cleanup_stale_port_process(DIFFUSION_SERVER_PORT)

        print("[engine_diffusion] Starting persistent diffusion server worker...", flush=True)
        py_exe = sys.executable
        env = os.environ.copy()
        env["DIFFUSION_WORKER"] = "1"
        env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")

        logs_dir = os.path.join(root_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        popen_kwargs = {}
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            popen_kwargs["startupinfo"] = si
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000

        with open(os.path.join(logs_dir, "diffusion_daemon.log"), "a", encoding="utf-8") as daemon_log:
            _server_proc = lifecycle.track(subprocess.Popen(
                [py_exe, os.path.abspath(__file__), "--server"],
                env=env,
                cwd=root_dir,
                stdout=daemon_log,
                stderr=daemon_log,
                **popen_kwargs
            ))
            _daemon_proc = _server_proc

        start_t = time.time()
        while time.time() - start_t < timeout:
            time.sleep(0.5)
            if check_server_status():
                print("[engine_diffusion] Persistent diffusion server worker is ready.", flush=True)
                return True
            if _server_proc and _server_proc.poll() is not None:
                print(f"[engine_diffusion] Server worker exited prematurely with code {_server_proc.poll()}.", flush=True)
                return False

        print("[engine_diffusion] Server startup timed out.", flush=True)
        return False


ensure_daemon_running = ensure_server_running


def unload_diffusion_models():
    """Unloads the persistent diffusion server, releasing GPU memory."""
    global _server_proc, _daemon_proc, _COMFY_NODE_CACHE, _active_checkpoint
    with _server_lock:
        try:
            import urllib.request
            req = urllib.request.Request(f"{DIFFUSION_SERVER_URL}/shutdown", method="POST", data=b"{}")
            urllib.request.urlopen(req, timeout=2.0)
        except Exception:
            pass

        if _server_proc is not None:
            try:
                _server_proc.terminate()
                _server_proc.wait(timeout=2.0)
            except Exception:
                try:
                    _server_proc.kill()
                except Exception:
                    pass
            _server_proc = None
            _daemon_proc = None

        _cleanup_stale_port_process(DIFFUSION_SERVER_PORT)

        _COMFY_NODE_CACHE.clear()
        _active_checkpoint = None
        gc.collect()


stop_server = unload_diffusion_models
stop_daemon = unload_diffusion_models


def execute_workflow_graph(
    workflow_path_or_dict: Any,
    replacements: Optional[Dict[str, Any]] = None,
    save_path: Optional[str] = None,
    empty_cache_after: bool = True
) -> Tuple[Optional[Any], str]:
    """Dynamically executes any ComfyUI node graph JSON in-process with AMD DirectML GPU acceleration."""
    comfy_dir = os.path.normpath(os.path.join(root_dir, "core", "comfy_engine"))
    if comfy_dir not in sys.path:
        sys.path.insert(0, comfy_dir)

    import folder_paths
    ckpt_dirs = [os.path.join(root_dir, "models", "checkpoints")]
    from variables.settings import COMFYUI_DIR
    comfy_ckpt_dir = os.path.normpath(os.path.join(COMFYUI_DIR, "models", "checkpoints"))
    if os.path.exists(comfy_ckpt_dir) and comfy_ckpt_dir not in ckpt_dirs:
        ckpt_dirs.append(comfy_ckpt_dir)
    folder_paths.folder_names_and_paths["checkpoints"] = (ckpt_dirs, folder_paths.supported_pt_extensions)
    folder_paths.folder_names_and_paths["loras"] = ([os.path.join(root_dir, "models", "loras")], folder_paths.supported_pt_extensions)
    folder_paths.folder_names_and_paths["vae"] = ([os.path.join(root_dir, "models", "vae")], folder_paths.supported_pt_extensions)
    folder_paths.folder_names_and_paths["ultralytics"] = ([os.path.join(root_dir, "models", "ultralytics")], folder_paths.supported_pt_extensions)

    import nodes
    if "FaceDetailer" not in nodes.NODE_CLASS_MAPPINGS:
        try:
            import logging, asyncio
            prev_level = logging.getLogger().level
            logging.getLogger().setLevel(logging.ERROR)
            asyncio.run(nodes.init_extra_nodes(init_custom_nodes=True))
            logging.getLogger().setLevel(prev_level)
        except Exception as custom_node_err:
            print(f"[engine_diffusion] Warning initializing custom nodes: {custom_node_err}")

    import comfy.model_management

    if isinstance(workflow_path_or_dict, str):
        with open(workflow_path_or_dict, "r", encoding="utf-8") as f:
            graph = json.load(f)
    else:
        import copy
        graph = copy.deepcopy(workflow_path_or_dict)

    if replacements:
        def _apply_replacements(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: _apply_replacements(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_apply_replacements(elem) for elem in obj]
            elif isinstance(obj, str):
                res = obj
                for placeholder, rep_val in replacements.items():
                    if placeholder in res:
                        if res == placeholder:
                            if isinstance(rep_val, int):
                                return rep_val
                            try:
                                if str(rep_val).isdigit() or (str(rep_val).startswith("-") and str(rep_val)[1:].isdigit()):
                                    return int(rep_val)
                            except (ValueError, TypeError):
                                pass
                        res = res.replace(placeholder, str(rep_val))
                return res
            return obj

        graph = _apply_replacements(graph)

    executed_outputs: Dict[str, Any] = {}

    def get_input_val(val: Any) -> Any:
        if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str) and val[0] in graph:
            src_id, src_out_idx = val[0], val[1]
            if src_id not in executed_outputs:
                execute_node(src_id)
            return executed_outputs[src_id][src_out_idx]
        return val

    def execute_node(node_id: str) -> Any:
        if node_id in executed_outputs:
            return executed_outputs[node_id]

        node_data = graph[node_id]
        class_type = node_data.get("class_type")
        if not class_type or class_type not in nodes.NODE_CLASS_MAPPINGS:
            print(f"[engine_diffusion] Skipping unmapped node [{node_id}] {class_type}")
            return None

        cls = nodes.NODE_CLASS_MAPPINGS[class_type]
        instance = cls()

        resolved_inputs = {}
        for inp_k, inp_v in node_data.get("inputs", {}).items():
            val = get_input_val(inp_v)
            if inp_k == "seed" and isinstance(val, str) and val.isdigit():
                val = int(val)
            resolved_inputs[inp_k] = val

        func_name = getattr(cls, "FUNCTION", "execute")
        func = getattr(instance, func_name)

        print(f"[engine_diffusion] Executing node [{node_id}] {class_type} -> {func_name}...")

        # Optimizations for DirectML GPU execution
        if class_type == "CheckpointLoaderSimple":
            ckpt_name = resolved_inputs.get("ckpt_name")
            cache_key = ("CheckpointLoaderSimple", ckpt_name)
            if cache_key in _COMFY_NODE_CACHE:
                print(f"[engine_diffusion] Reusing cached checkpoint model: {ckpt_name}")
                executed_outputs[node_id] = _COMFY_NODE_CACHE[cache_key]
                return executed_outputs[node_id]

            outs = func(**resolved_inputs)
            _COMFY_NODE_CACHE[cache_key] = outs
            executed_outputs[node_id] = outs
            return outs

        if class_type == "LoraLoader":
            lora_name = resolved_inputs.get("lora_name")
            sm = float(resolved_inputs.get("strength_model", 1.0))
            sc = float(resolved_inputs.get("strength_clip", 1.0))
            m_in = resolved_inputs.get("model")
            c_in = resolved_inputs.get("clip")

            is_placeholder = isinstance(lora_name, str) and lora_name.startswith("%") and lora_name.endswith("%")
            if not lora_name or is_placeholder or (sm == 0 and sc == 0):
                print(f"[engine_diffusion] Bypassing LoRA node [{node_id}]: {lora_name}")
                executed_outputs[node_id] = (m_in, c_in)
                return executed_outputs[node_id]
            if not folder_paths.get_full_path("loras", lora_name):
                raise FileNotFoundError(f"LoRA not found: {lora_name} (workflow node {node_id}). Place it in models/loras.")

            cache_key = ("LoraLoader", lora_name, sm, sc, id(m_in), id(c_in))
            if cache_key in _COMFY_NODE_CACHE:
                print(f"[engine_diffusion] Reusing cached LoRA weights: {lora_name}")
                executed_outputs[node_id] = _COMFY_NODE_CACHE[cache_key]
                return executed_outputs[node_id]

            outs = func(**resolved_inputs)
            _COMFY_NODE_CACHE[cache_key] = outs
            executed_outputs[node_id] = outs
            return outs

        if class_type == "UltralyticsDetectorProvider":
            m_name = resolved_inputs.get("model_name")
            cache_key = ("UltralyticsDetectorProvider", m_name)
            if cache_key in _COMFY_NODE_CACHE:
                print(f"[engine_diffusion] Reusing cached detector: {m_name}")
                executed_outputs[node_id] = _COMFY_NODE_CACHE[cache_key]
                return executed_outputs[node_id]

            outs = func(**resolved_inputs)
            _COMFY_NODE_CACHE[cache_key] = outs
            executed_outputs[node_id] = outs
            return outs

        outs = func(**resolved_inputs)
        executed_outputs[node_id] = outs

        if class_type in ("KSampler", "VAEDecode", "FaceDetailer"):
            gc.collect()
            try:
                import comfy.model_management as mm
                mm.soft_empty_cache()
            except Exception:
                pass
            try:
                import torch_directml
                if hasattr(torch_directml, "empty_cache"):
                    torch_directml.empty_cache()
            except Exception:
                pass

        return outs

    final_images = None
    with torch.inference_mode():
        # Priority search for terminal output node (PreviewImage / SaveImage -> FaceDetailer -> VAEDecode)
        target_nid = None
        for ptype in ("PreviewImage", "SaveImage", "FaceDetailer", "VAEDecode"):
            for nid, nd in graph.items():
                if nd.get("class_type") == ptype:
                    target_nid = nid
                    break
            if target_nid:
                break

        if target_nid:
            res = execute_node(target_nid)
            if res is not None:
                if isinstance(res, (list, tuple)) and len(res) > 0 and hasattr(res[0], "shape"):
                    final_images = res[0]
                elif isinstance(res, dict) and "result" in res and isinstance(res["result"], (list, tuple)) and len(res["result"]) > 0:
                    final_images = res["result"][0]
                elif isinstance(res, dict) and "images" in res:
                    final_images = res["images"]

        # Search executed outputs for any rendered image tensor if final_images wasn't directly returned by target_nid
        if final_images is None:
            for nid in reversed(list(executed_outputs.keys())):
                out = executed_outputs[nid]
                if isinstance(out, (list, tuple)) and len(out) > 0 and hasattr(out[0], "shape") and len(out[0].shape) == 4:
                    final_images = out[0]
                    break

    from PIL import Image
    import numpy as np

    result_image = None
    if final_images is not None:
        img_array = (final_images[0].detach().cpu().numpy() * 255).astype(np.uint8)
        result_image = Image.fromarray(img_array)
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            result_image.save(save_path)
            print(f"[engine_diffusion] Image saved dynamically to {save_path}")

    # Free intermediate node outputs from memory
    executed_outputs.clear()
    del final_images
    if empty_cache_after:
        gc.collect()
        try:
            import comfy.model_management as mm
            mm.soft_empty_cache()
        except Exception:
            pass
        try:
            import torch_directml
            if hasattr(torch_directml, "empty_cache"):
                torch_directml.empty_cache()
        except Exception:
            pass

    if result_image is not None:
        return result_image, save_path or ""

    return None, ""


SHARED_IMAGE_WORKFLOW = os.path.join(root_dir, "models", "ImageWorkflow.json")
DEFAULT_IMAGE_WORKFLOW = os.path.join(root_dir, "models", "ImageWorkflow.default.json")
IMAGE_WIDTH = 832
IMAGE_HEIGHT = 1248


def resolve_image_workflow_path(follower_id: Optional[str] = None) -> str:
    """Returns the image workflow that defines how images are generated:
    the follower's own core/followers/<follower_id>/ImageWorkflow.json, else models/ImageWorkflow.json,
    else the bundled models/ImageWorkflow.default.json."""
    if follower_id:
        from variables.settings import FOLLOWERS_DIR
        follower_wf = os.path.join(FOLLOWERS_DIR, follower_id, "ImageWorkflow.json")
        if os.path.exists(follower_wf):
            return follower_wf
    if os.path.exists(SHARED_IMAGE_WORKFLOW):
        return SHARED_IMAGE_WORKFLOW
    return DEFAULT_IMAGE_WORKFLOW


def _generate_portrait_image_inprocess(
    prompt: str,
    negative_prompt: str = "",
    checkpoint: Optional[str] = None,
    seed: Optional[int] = None,
    workflow_path: Optional[str] = None,
    save_path: Optional[str] = None,
    save_paths: Optional[List[str]] = None,
    **kwargs: Any
) -> Any:
    """Runs the image workflow graph in-process. Every generation setting comes from the workflow;
    this function fills its placeholders (%prompt%, %negative_prompt%, %seed%, %model%, %width%, %height%).
    With save_paths, one image is generated per path (seed offset per slot) and the list of saved paths is returned."""
    if seed is None or seed < 0:
        seed = random.randint(1, 2147483647)

    wf_file = workflow_path or resolve_image_workflow_path()
    if not os.path.exists(wf_file):
        raise FileNotFoundError(f"Image workflow not found: {wf_file}")
    print(f"[engine_diffusion] Running workflow: {wf_file} ({IMAGE_WIDTH}x{IMAGE_HEIGHT})")
    model_name = checkpoint or get_active_checkpoint() or resolve_checkpoint_name()

    def _run(target_path: str, slot_seed: int, last: bool) -> str:
        replacements = {
            "%prompt%": prompt,
            "%negative_prompt%": negative_prompt,
            "%seed%": slot_seed,
            "%model%": model_name,
            "%width%": IMAGE_WIDTH,
            "%height%": IMAGE_HEIGHT,
        }
        _, out_path = execute_workflow_graph(wf_file, replacements=replacements, save_path=target_path, empty_cache_after=last)
        if not out_path or not os.path.exists(out_path):
            raise RuntimeError(f"Workflow produced no image: {wf_file}")
        return out_path

    if save_paths is not None:
        return [_run(p, seed + idx, idx == len(save_paths) - 1) for idx, p in enumerate(save_paths)]
    return _run(save_path, seed, True)


def generate_portrait_image(
    prompt: str,
    negative_prompt: str = "",
    checkpoint: Optional[str] = None,
    seed: Optional[int] = None,
    workflow_path: Optional[str] = None,
    save_path: Optional[str] = None,
    save_paths: Optional[List[str]] = None,
    **kwargs: Any
) -> Any:
    """Generates one image (save_path) or one per entry of save_paths (returns the list of paths)."""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "checkpoint": checkpoint or get_active_checkpoint(),
        "seed": seed,
        "workflow_path": workflow_path,
        "save_path": save_path,
        "save_paths": save_paths,
    }

    if os.getenv("DIFFUSION_WORKER") == "1":
        return _generate_portrait_image_inprocess(**payload)

    for attempt in range(2):
        if not ensure_server_running():
            raise RuntimeError("Failed to start persistent diffusion server worker.")

        import urllib.request
        import urllib.error

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{DIFFUSION_SERVER_URL}/generate",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                if res_json.get("status") == "ok":
                    if "paths" in res_json:
                        return res_json.get("paths", [])
                    return res_json.get("path", "")
                else:
                    raise RuntimeError(res_json.get("error", "Unknown diffusion error"))
        except urllib.error.HTTPError as http_err:
            detail = str(http_err)
            try:
                err_body = json.loads(http_err.read().decode("utf-8"))
                detail = err_body.get("error", detail)
            except Exception:
                pass

            is_device_err = any(k in detail.lower() for k in ("suspended", "device removed", "device lost", "0x887a0005"))
            if attempt == 0 and is_device_err:
                print(f"[engine_diffusion] GPU device was suspended ({detail}). Restarting worker for clean GPU context...", flush=True)
                unload_diffusion_models()
                if ensure_server_running():
                    continue

            raise RuntimeError(f"Diffusion error: {detail}") from http_err
        except Exception as conn_err:
            if attempt == 0:
                print(f"[engine_diffusion] Connection to worker failed ({conn_err}). Restarting worker...", flush=True)
                unload_diffusion_models()
                if ensure_server_running():
                    continue
            raise conn_err


if __name__ == "__main__":
    import argparse
    from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Run as HTTP diffusion server")
    args = parser.parse_args()

    if args.server:
        _gen_lock = threading.Lock()
        _is_busy = False

        class DiffusionHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress access logs

            def do_GET(self):
                if self.path == "/health":
                    status = "busy" if _is_busy else "ready"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": status}).encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                global _is_busy
                if self.path == "/generate":
                    content_len = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_len)
                    with _gen_lock:
                        _is_busy = True
                        try:
                            cfg = json.loads(body.decode("utf-8"))
                            out_path = _generate_portrait_image_inprocess(**cfg)
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            if isinstance(out_path, list):
                                body_out = {"status": "ok", "paths": out_path}
                            else:
                                body_out = {"status": "ok", "path": out_path}
                            self.wfile.write(json.dumps(body_out).encode("utf-8"))
                        except Exception as ex:
                            import traceback
                            traceback.print_exc()
                            self.send_response(500)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "error", "error": str(ex)}).encode("utf-8"))
                        finally:
                            _is_busy = False
                elif self.path == "/shutdown":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"shutting_down"}')
                    threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0))).start()
                else:
                    self.send_response(404)
                    self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", DIFFUSION_SERVER_PORT), DiffusionHandler)
        server.daemon_threads = True
        print(f"[engine_diffusion server] Listening on http://127.0.0.1:{DIFFUSION_SERVER_PORT}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
