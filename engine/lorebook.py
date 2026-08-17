"""
engine/lorebook.py — Canonical re-export of utils.lorebook.
Consolidates lorebook engine paths to a single source of truth.
"""

from utils.lorebook import (
    get_active_lore,
    list_lorebooks,
    import_lorebook,
    delete_lorebook,
    _parse_lorebook,
    _normalise_entry,
)

__all__ = [
    "get_active_lore",
    "list_lorebooks",
    "import_lorebook",
    "delete_lorebook",
    "_parse_lorebook",
    "_normalise_entry",
]
