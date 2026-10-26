"""
utils/shutdown.py — Backward-compatible wrapper delegating to utils.lifecycle.
"""

from utils.lifecycle import shutdown, track

close_app_processes = shutdown

__all__ = ["shutdown", "track", "close_app_processes"]
