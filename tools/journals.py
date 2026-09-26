"""
tools/journals.py — Re-exports core.journals for tool and caller compatibility.
"""
from core.journals import (
    get_journal_entries,
    save_journal_entries,
    add_journal_entry,
    delete_journal_entry,
    match_journals,
)

__all__ = [
    "get_journal_entries",
    "save_journal_entries",
    "add_journal_entry",
    "delete_journal_entry",
    "match_journals",
]
