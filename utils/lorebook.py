"""
utils/lorebook.py — ST-compatible hybrid lorebook engine (Keyword + Vector).

Loads World Info entries from:
  1. data.character_book in the active follower's card JSON
  2. Standalone .json files in core/followers/<follower>/lorebooks/
  3. Global World & Mechanics Lorebooks (core/lorebooks/)

Normalizes both ST standalone dict-of-entries and chara_card_v3
list-of-entries formats into a single internal schema, then executes
hybrid matching:
  - Deterministic: Constant entries & exact keyword matching (keys + secondary_keys)
  - Semantic: Vector embeddings via SentenceTransformer / MiniLM-L6 with in-memory caching
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from typing import Any

# In-memory vector cache keyed by entry content hash: {hash: np.ndarray}
_entry_vector_cache: dict[str, Any] = {}
SEMANTIC_THRESHOLD: float = 0.38
MAX_SEMANTIC_MATCHES: int = 4
DEFAULT_SCAN_DEPTH: int = 4  # messages (not turns)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _normalise_entry(raw: dict) -> dict | None:
    if raw.get("disable", False):
        return None
    if not raw.get("enabled", True):
        return None

    content = (raw.get("content") or "").strip()
    if not content:
        return None

    # Primary keys — standalone uses 'key', v3 uses 'keys'
    keys = raw.get("keys") or raw.get("key") or []
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split(",") if k.strip()]

    sec_keys = raw.get("secondary_keys") or raw.get("keysecondary") or []
    if isinstance(sec_keys, str):
        sec_keys = [k.strip() for k in sec_keys.split(",") if k.strip()]

    # Position: ST standalone 0=before, 1=after; v3 string
    pos_raw = raw.get("position", 0)
    if isinstance(pos_raw, str):
        position = "after" if "after" in pos_raw else "before"
    else:
        position = "after" if pos_raw == 1 else "before"

    order = raw.get("insertion_order") or raw.get("order") or 100
    scan_depth = raw.get("scan_depth")

    return {
        "keys":          [k.lower() for k in keys],
        "secondary_keys":[k.lower() for k in sec_keys],
        "content":       content,
        "constant":      bool(raw.get("constant", False)),
        "selective":     bool(raw.get("selective", False)),
        "position":      position,
        "order":         int(order),
        "scan_depth":    int(scan_depth) if scan_depth is not None else None,
        "probability":   int(raw.get("probability", 100)),
    }


def _parse_lorebook(book: dict) -> list[dict]:
    raw_entries = book.get("entries", [])
    if isinstance(raw_entries, dict):
        raw_entries = list(raw_entries.values())
    return [e for raw in raw_entries if (e := _normalise_entry(raw)) is not None]


# ---------------------------------------------------------------------------
# Matching: Keyword & Vector
# ---------------------------------------------------------------------------

def _matches_keys(keys: list[str], scan_text: str) -> bool:
    return any(k and k in scan_text for k in keys)


def _entry_keyword_triggers(entry: dict, scan_text: str) -> bool:
    if entry["constant"]:
        return True
    if not _matches_keys(entry["keys"], scan_text):
        return False
    if entry["selective"] and entry["secondary_keys"]:
        if not _matches_keys(entry["secondary_keys"], scan_text):
            return False
    if entry["probability"] < 100:
        if random.randint(1, 100) > entry["probability"]:
            return False
    return True


def _compute_entry_hash(entry: dict) -> str:
    key_str = ",".join(entry["keys"])
    raw = f"{key_str}::{entry['content']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_embedding_model():
    try:
        from core.skills.vectorized_databank.databank import get_embedding_model
        return get_embedding_model()
    except Exception as e:
        print(f"[lorebook] Embedding model unavailable for vector retrieval: {e}")
        return None


def _perform_vector_scan(
    candidate_entries: list[dict],
    query_text: str,
    threshold: float = SEMANTIC_THRESHOLD,
    max_matches: int = MAX_SEMANTIC_MATCHES,
) -> list[dict]:
    """Computes semantic similarity for candidate lorebook entries against query text."""
    if not candidate_entries or not query_text.strip():
        return []

    try:
        import numpy as np
        model = _get_embedding_model()
        if model is None:
            return []

        # 1. Encode query
        query_vec = model.encode(query_text)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        # 2. Ensure all candidate entries have cached embeddings
        uncached_entries = []
        uncached_texts = []
        uncached_hashes = []

        for entry in candidate_entries:
            e_hash = _compute_entry_hash(entry)
            if e_hash not in _entry_vector_cache:
                uncached_entries.append(entry)
                # Combine keys and content for comprehensive representation
                keys_prefix = f"Keys: {', '.join(entry['keys'])}\n" if entry["keys"] else ""
                uncached_texts.append(f"{keys_prefix}{entry['content']}")
                uncached_hashes.append(e_hash)

        if uncached_texts:
            new_vectors = model.encode(uncached_texts)
            for h, vec in zip(uncached_hashes, new_vectors):
                _entry_vector_cache[h] = vec

        # 3. Calculate cosine similarity
        scored_entries: list[tuple[float, dict]] = []
        for entry in candidate_entries:
            if entry["probability"] < 100:
                if random.randint(1, 100) > entry["probability"]:
                    continue

            e_hash = _compute_entry_hash(entry)
            vec = _entry_vector_cache.get(e_hash)
            if vec is None:
                continue

            entry_norm = np.linalg.norm(vec)
            if entry_norm == 0:
                continue

            similarity = float(np.dot(query_vec, vec) / (query_norm * entry_norm))
            if similarity >= threshold:
                # If selective is set, ensure secondary keys are respected if present
                if entry["selective"] and entry["secondary_keys"]:
                    if not _matches_keys(entry["secondary_keys"], query_text.lower()):
                        continue
                scored_entries.append((similarity, entry))

        scored_entries.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored_entries[:max_matches]]

    except Exception as e:
        print(f"[lorebook] Vector search error: {e}")
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_active_lore(
    follower_id: str,
    recent_messages: list[dict],
    followers_dir: str | None = None,
) -> tuple[list[str], list[str]]:
    """
    Return (before_entries, after_entries) — triggered lore content strings.
    Hybrid matching: Evaluates keyword triggers, then semantic vector triggers.
    Scans:
      1. Global World & Mechanics Lorebooks (core/lorebooks/)
      2. Follower Card character_book
      3. Follower-specific lorebooks (core/followers/<follower_id>/lorebooks/)
    """
    if followers_dir is None:
        from variables import FOLLOWERS_DIR
        followers_dir = FOLLOWERS_DIR

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    global_lore_dir = os.path.join(base_dir, "core", "lorebooks")
    follower_dir = os.path.join(followers_dir, follower_id)
    all_entries: list[dict] = []

    # 1. Global World & Mechanics Lorebooks
    if os.path.isdir(global_lore_dir):
        for root, _, files in os.walk(global_lore_dir):
            for fname in files:
                if fname.endswith(".json"):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            all_entries.extend(_parse_lorebook(json.load(f)))
                    except Exception as e:
                        print(f"[lorebook] Error reading global lorebook {fname}: {e}")

    # 2. character_book from card
    card_path = os.path.join(follower_dir, f"{follower_id}.json")
    if os.path.exists(card_path):
        try:
            with open(card_path, encoding="utf-8") as f:
                card_raw = json.load(f)
            cb = card_raw.get("data", card_raw).get("character_book")
            if cb:
                all_entries.extend(_parse_lorebook(cb))
        except Exception as e:
            print(f"[lorebook] Error reading card: {e}")

    # 3. Follower-specific lorebook files
    lorebooks_dir = os.path.join(follower_dir, "lorebooks")
    if os.path.isdir(lorebooks_dir):
        for fname in os.listdir(lorebooks_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(lorebooks_dir, fname), encoding="utf-8") as f:
                    all_entries.extend(_parse_lorebook(json.load(f)))
            except Exception as e:
                print(f"[lorebook] Error reading {fname}: {e}")

    if not all_entries:
        return [], []

    # 4. Build scan window
    max_depth = max(
        (e["scan_depth"] for e in all_entries if e["scan_depth"] is not None),
        default=DEFAULT_SCAN_DEPTH,
    )
    scan_msgs = [
        m for m in recent_messages
        if m.get("role") in ("user", "follower", "program") and (m.get("text") or "").strip()
    ]
    scan_text = " ".join(
        (m.get("text") or "").lower() for m in scan_msgs[-max_depth:]
    )

    # 5. Hybrid matching:
    # A. Deterministic keyword / constant pass
    keyword_triggered = [e for e in all_entries if _entry_keyword_triggers(e, scan_text)]
    keyword_set = set(id(e) for e in keyword_triggered)

    # B. Vector semantic pass for non-triggered entries
    non_triggered_candidates = [e for e in all_entries if id(e) not in keyword_set and not e["constant"]]
    vector_triggered = _perform_vector_scan(non_triggered_candidates, scan_text)

    # Combine all triggered entries and sort by order
    combined_triggered = keyword_triggered + [e for e in vector_triggered if id(e) not in keyword_set]
    combined_triggered.sort(key=lambda e: e["order"])

    before = [e["content"] for e in combined_triggered if e["position"] == "before"]
    after  = [e["content"] for e in combined_triggered if e["position"] == "after"]
    return before, after


# ---------------------------------------------------------------------------
# File management helpers
# ---------------------------------------------------------------------------

def list_lorebooks(follower_id: str, followers_dir: str | None = None) -> list[dict]:
    if followers_dir is None:
        from variables import FOLLOWERS_DIR
        followers_dir = FOLLOWERS_DIR

    results = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    global_lore_dir = os.path.join(base_dir, "core", "lorebooks")

    # 1. Global Core Lorebooks
    if os.path.isdir(global_lore_dir):
        for root, _, files in os.walk(global_lore_dir):
            for fname in sorted(files):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        book = json.load(f)
                    rel_category = os.path.basename(root).title()
                    book_name = book.get("name") or fname.replace(".json", "").replace("_", " ").title()
                    results.append({
                        "id": f"global_{fname}",
                        "name": f"{book_name} ({rel_category})",
                        "source": "world",
                        "scope": "World & Rules",
                        "entry_count": len(_parse_lorebook(book)),
                        "filename": fname,
                        "readonly": True
                    })
                except Exception:
                    pass

    # 2. Card Embedded Lorebook
    card_path = os.path.join(followers_dir, follower_id, f"{follower_id}.json")
    if os.path.exists(card_path):
        try:
            with open(card_path, encoding="utf-8") as f:
                card_raw = json.load(f)
            cb = card_raw.get("data", card_raw).get("character_book")
            if cb:
                results.append({
                    "id": "__card__",
                    "name": cb.get("name") or f"{follower_id} (Card Embedded)",
                    "source": "card",
                    "scope": "Follower Card",
                    "entry_count": len(_parse_lorebook(cb)),
                })
        except Exception:
            pass

    # 3. Follower-specific Lorebooks
    lorebooks_dir = os.path.join(followers_dir, follower_id, "lorebooks")
    if os.path.isdir(lorebooks_dir):
        for fname in sorted(os.listdir(lorebooks_dir)):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(lorebooks_dir, fname), encoding="utf-8") as f:
                    book = json.load(f)
                results.append({
                    "id": fname,
                    "name": book.get("name") or fname.replace(".json", "").title(),
                    "source": "file",
                    "scope": "Follower Custom",
                    "entry_count": len(_parse_lorebook(book)),
                    "filename": fname,
                })
            except Exception:
                pass

    return results


def import_lorebook(follower_id: str, book_data: dict, filename: str, followers_dir: str | None = None) -> str:
    if followers_dir is None:
        from variables import FOLLOWERS_DIR
        followers_dir = FOLLOWERS_DIR
    lorebooks_dir = os.path.join(followers_dir, follower_id, "lorebooks")
    os.makedirs(lorebooks_dir, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
    if not safe.endswith(".json"):
        safe += ".json"
    dest = os.path.join(lorebooks_dir, safe)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(book_data, f, indent=2, ensure_ascii=False)
    return dest


def delete_lorebook(follower_id: str, filename: str, followers_dir: str | None = None) -> bool:
    if followers_dir is None:
        from variables import FOLLOWERS_DIR
        followers_dir = FOLLOWERS_DIR
    fpath = os.path.join(followers_dir, follower_id, "lorebooks", filename)
    if os.path.exists(fpath):
        os.remove(fpath)
        return True
    return False

