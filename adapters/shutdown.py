"""
adapters/shutdown.py — Closes every process the app started when the app exits.

Covers the LLM server, the diffusion server, ComfyUI, and any other Python process
launched from this app. Registered once at import; desktop.py also calls it directly
before its hard exit.
"""

import os
import atexit

import psutil

PROJECT_DIR = os.path.normcase(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _is_app_process(proc: psutil.Process) -> bool:
    """True for Python processes and binaries shipped inside the project (e.g. llama-server)."""
    try:
        name = proc.name().lower()
        exe = os.path.normcase(proc.exe() or "")
    except psutil.Error:
        return False
    return name.startswith("python") or exe.startswith(PROJECT_DIR)


def close_app_processes():
    """Kills every app-started process, then stops ComfyUI by port in case it restarted itself
    outside this process tree (ComfyUI-Manager reboots do this)."""
    try:
        children = psutil.Process().children(recursive=True)
    except psutil.Error:
        children = []

    targets = [p for p in children if _is_app_process(p)]
    for proc in targets:
        try:
            proc.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(targets, timeout=3)

    from adapters import comfy_manager
    if comfy_manager.check_comfy_running(force_refresh=True):
        comfy_manager.stop_comfy_server()


def _on_exit():
    # The Flask reloader worker restarts on code changes; the reloader parent owns cleanup on real exit.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return
    close_app_processes()


atexit.register(_on_exit)
