import os
import json
import uuid
import time
import re
from runners.follower import get_active_follower
from variables.settings import FOLLOWERS_DIR

def get_journal_entries(follower_id: str = None) -> list:
    try:
        from core.save_manager import get_active_save_id, read_save, write_save
        save_id = get_active_save_id()
        bundle = read_save(save_id)
        
        # 1. Direct journals key
        journals = bundle.get("journals")
        if isinstance(journals, list) and journals:
            return journals
            
        # 2. Check if legacy save placed journal entries inside databank
        db_val = bundle.get("databank")
        if isinstance(db_val, list) and db_val:
            # Check if these are journal entries (with 'keyphrases' or 'content')
            if any("keyphrases" in e or "content" in e for e in db_val if isinstance(e, dict)):
                bundle["journals"] = db_val
                bundle["databank"] = {"documents": [], "chunks": []}
                write_save(save_id, bundle)
                return db_val
                
        if isinstance(journals, list):
            return journals
    except Exception as e:
        print(f"Error loading journals from save bundle: {e}")
    return []

def save_journal_entries(entries: list, follower_id: str = None):
    try:
        from core.save_manager import get_active_save_id, read_save, write_save
        save_id = get_active_save_id()
        bundle = read_save(save_id)
        bundle["journals"] = entries
        # Ensure databank is properly structured if it was previously a list
        if isinstance(bundle.get("databank"), list):
            bundle["databank"] = {"documents": [], "chunks": []}
        write_save(save_id, bundle)
    except Exception as e:
        print(f"Error saving journals to save bundle: {e}")

def add_journal_entry(keyphrases_str: str, content: str, follower_id: str = None) -> dict:
    entries = get_journal_entries(follower_id)
    
    # Normalize keyphrases to lowercase list
    keyphrases = [k.strip().lower() for k in keyphrases_str.split(",") if k.strip()]
    
    entry = {
        "id": str(uuid.uuid4()),
        "keyphrases": keyphrases,
        "content": content.strip()[:300],  # Keep it small and focused (max 300 chars)
        "timestamp": time.time()
    }
    try:
        from core.skills.vectorized_databank.databank import get_embedding_model
        model = get_embedding_model()
        vec = model.encode(entry["content"])
        entry["vector"] = vec.tolist() if hasattr(vec, "tolist") else list(vec)
    except Exception as e:
        print(f"[Journals] Pre-embedding failed during add_journal_entry: {e}")

    entries.append(entry)
    save_journal_entries(entries, follower_id)
    return entry

def delete_journal_entry(entry_id: str, follower_id: str = None) -> bool:
    entries = get_journal_entries(follower_id)
    initial_len = len(entries)
    entries = [e for e in entries if e.get("id") != entry_id]
    if len(entries) < initial_len:
        save_journal_entries(entries, follower_id)
        return True
    return False

def match_journals(user_message: str, follower_id: str = None, query_vector=None) -> list:
    """Finds top 3 matching journal entries using keyword matching with vector similarity fallback."""
    if not user_message:
        return []
        
    entries = get_journal_entries(follower_id)
    if not entries:
        return []
        
    # Fast path: keyword matching
    msg_clean = user_message.lower()
    matched = []
    
    for entry in entries:
        kps = entry.get("keyphrases", [])
        content = entry.get("content", "")
        if not content:
            continue
            
        score = 0
        for kp in kps:
            # Word boundary check for short keyphrases, substring check for multi-word phrases
            if len(kp) <= 3:
                # Require word boundaries for very short words (e.g. 'cat', 'job')
                pattern = r'\b' + re.escape(kp) + r'\b'
                if re.search(pattern, msg_clean):
                    score += 1
            else:
                # Substring check for longer phrases
                if kp in msg_clean:
                    score += len(kp) # longer matches get higher weight
                    
        if score > 0:
            matched.append((score, entry))
            
    # Sort by score descending, then by timestamp descending
    matched.sort(key=lambda x: (x[0], x[1].get("timestamp", 0)), reverse=True)
    
    if matched:
        return [item[1] for item in matched[:3]]
    
    # Semantic fallback: vector similarity when keyword matching finds nothing
    try:
        import numpy as np

        if query_vector is not None:
            query_vec = np.array(query_vector, dtype=float)
        else:
            from core.skills.vectorized_databank.databank import get_embedding_model
            model = get_embedding_model()
            query_vec = np.array(model.encode(user_message), dtype=float)

        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        # Batch-encode any entries missing a stored vector (legacy data migration)
        missing_entries = [e for e in entries if not e.get("vector") and e.get("content")]
        if missing_entries:
            try:
                from core.skills.vectorized_databank.databank import get_embedding_model
                model = get_embedding_model()
                texts = [e["content"] for e in missing_entries]
                encoded_vecs = model.encode(texts)
                for e, vec in zip(missing_entries, encoded_vecs):
                    e["vector"] = vec.tolist() if hasattr(vec, "tolist") else list(vec)
                save_journal_entries(entries, follower_id)
                if follower_id:
                    f_json = os.path.join(FOLLOWERS_DIR, follower_id, "journals.json")
                    if os.path.exists(f_json):
                        with open(f_json, "w", encoding="utf-8") as f:
                            json.dump(entries, f, indent=2)
            except Exception as mig_err:
                print(f"[Journals] Legacy vector migration error: {mig_err}")

        semantic_matched = []
        for entry in entries:
            vec_data = entry.get("vector")
            if not vec_data:
                continue
            content_vec = np.array(vec_data, dtype=float)
            content_norm = np.linalg.norm(content_vec)
            if content_norm == 0:
                continue
            similarity = float(np.dot(query_vec, content_vec) / (query_norm * content_norm))
            if similarity >= 0.35:
                semantic_matched.append((similarity, entry))

        semantic_matched.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in semantic_matched[:3]]
    except Exception as e:
        print(f"[Journals] Semantic fallback error: {e}")
        return []

