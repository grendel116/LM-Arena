import os
import json
import time
import requests
import numpy as np
from bs4 import BeautifulSoup

# Lazy-loaded embedding model to speed up server boot and reload times
_embedding_model = None
_embedding_model_unavailable = False

def get_embedding_model():
    global _embedding_model, _embedding_model_unavailable
    if _embedding_model_unavailable:
        raise RuntimeError("SentenceTransformer model is unavailable in the current environment.")
    if _embedding_model is None:
        try:
            print(">>> Initializing SentenceTransformer model ('all-MiniLM-L6-v2')...")
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print(">>> SentenceTransformer model loaded successfully.")
        except Exception as e:
            _embedding_model_unavailable = True
            print(f">>> SentenceTransformer unavailable: {e}")
            raise e
    return _embedding_model


class DataBankManager:
    def __init__(self, follower_id: str = None, save_id: str = None, db_dir=None):
        from runners.follower import get_active_follower
        from core.save_manager import get_active_save_id
        self.follower_id = follower_id or get_active_follower()
        self.follower_id = self.follower_id
        self.save_id = save_id or get_active_save_id()
        
        # Follower-bound databank file path (core/followers/<follower_id>/databank.json)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.follower_dir = os.path.join(base_dir, "core", "followers", self.follower_id)
        self.db_path = os.path.join(self.follower_dir, "databank.json")
        self.memories_path = "memories"  # Save-bound key

    def _load_data(self, path):
        if str(path) == "memories":
            # Save-bound memory compactions
            try:
                from core.save_manager import read_save, get_active_save_id
                save_id = self.save_id or get_active_save_id()
                bundle = read_save(save_id)
                val = bundle.get("memories")
                if isinstance(val, dict):
                    val.setdefault("documents", [])
                    val.setdefault("chunks", [])
                    return val
            except Exception as e:
                print(f"Error loading save memories data: {e}")
            return {"documents": [], "chunks": []}
        else:
            # Follower-bound databank JSON file
            try:
                if os.path.exists(self.db_path):
                    with open(self.db_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        data.setdefault("documents", [])
                        data.setdefault("chunks", [])
                        return data
            except Exception as e:
                print(f"Error loading follower databank from {self.db_path}: {e}")
            return {"documents": [], "chunks": []}

    def _save_data(self, path, data):
        if str(path) == "memories":
            # Save-bound memory compactions
            try:
                from core.save_manager import read_save, write_save, get_active_save_id
                save_id = self.save_id or get_active_save_id()
                bundle = read_save(save_id)
                bundle["memories"] = data
                write_save(save_id, bundle)
            except Exception as e:
                print(f"Error saving save memories data: {e}")
        else:
            # Follower-bound databank JSON file
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
                temp_path = f"{self.db_path}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.db_path)
            except Exception as e:
                print(f"Error saving follower databank to {self.db_path}: {e}")


    def clean_html(self, html_content: str) -> str:
        """Parses HTML and extracts clean readable text, removing boilerplate markup."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script, style, header, footer, nav, and metadata elements
        for element in soup(["script", "style", "nav", "header", "footer", "form", "noscript", "aside"]):
            element.decompose()
            
        text = soup.get_text(separator=' ')
        
        # Consolidate whitespaces and empty lines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return clean_text

    def scrape_url(self, url: str) -> str:
        """Fetches a webpage and scrapes clean plain text from it."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        return self.clean_html(res.text)

    def extract_pdf_text(self, file_path: str) -> str:
        """Tries to extract text from a PDF file using pypdf."""
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
            return "\n\n".join(text_parts)
        except ImportError:
            raise ImportError("The 'pypdf' package is required to parse PDF uploads. Please install it with 'pip install pypdf'.")

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list:
        """Splits text into chunks of clean sentences/lines with rolling overlap."""
        if not text:
            return []
            
        # Standard recursive character splitter simulation
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # If a single paragraph is larger than the chunk size, split by lines or sentences
            if len(para) > chunk_size:
                sentences = para.replace('. ', '.\n').split('\n')
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if current_length + len(sent) > chunk_size and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        # Keep last items for overlap
                        overlap_text = []
                        overlap_len = 0
                        for c in reversed(current_chunk):
                            if overlap_len + len(c) < overlap:
                                overlap_text.insert(0, c)
                                overlap_len += len(c)
                            else:
                                break
                        current_chunk = overlap_text
                        current_length = overlap_len
                    current_chunk.append(sent)
                    current_length += len(sent)
            else:
                if current_length + len(para) > chunk_size and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    # Keep overlap
                    overlap_text = []
                    overlap_len = 0
                    for c in reversed(current_chunk):
                        if overlap_len + len(c) < overlap:
                            overlap_text.insert(0, c)
                            overlap_len += len(c)
                        else:
                            break
                    current_chunk = overlap_text
                    current_length = overlap_len
                current_chunk.append(para)
                current_length += len(para)
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return [c.strip() for c in chunks if c.strip()]

    def ingest_text(self, text: str, name: str, source_type: str, doc_id: str = None) -> str:
        """Chunks, embeds, and saves a text document to the local JSON files."""
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())
            
        chunks = self.chunk_text(text)
        if not chunks:
            return doc_id
            
        # Generate embeddings in batch
        model = get_embedding_model()
        vectors = model.encode(chunks)
        
        # Decide which database file to use
        is_chat_history = (source_type == 'chat_history')
        path = self.memories_path if is_chat_history else self.db_path
        
        data = self._load_data(path)
        
        # Insert document reference
        data["documents"].append({
            "id": doc_id,
            "name": name,
            "source_type": source_type,
            "size": len(text),
            "timestamp": time.time()
        })
        
        # Insert chunk vectors
        for idx, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            data["chunks"].append({
                "doc_id": doc_id,
                "chunk_index": idx,
                "text": chunk_text,
                "vector": vector.tolist()
            })
            
        self._save_data(path, data)
        print(f"[Data Bank] Ingested document '{name}' ({len(chunks)} chunks) into {'journal' if is_chat_history else 'databank'}.")
        return doc_id

    def ingest_file(self, file_path: str, original_filename: str) -> str:
        """Parses file type, extracts text, and ingests it."""
        ext = os.path.splitext(original_filename)[1].lower()
        
        if ext in ['.txt', '.md', '.py']:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            return self.ingest_text(text, original_filename, "file")
            
        elif ext in ['.html', '.htm']:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()
            clean_text = self.clean_html(html)
            return self.ingest_text(clean_text, original_filename, "file")
            
        elif ext == '.pdf':
            clean_text = self.extract_pdf_text(file_path)
            return self.ingest_text(clean_text, original_filename, "file")
            
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def ingest_url(self, url: str) -> str:
        """Scrapes webpage URL and ingests it."""
        clean_text = self.scrape_url(url)
        # Clean URL to get a readable name
        name = url.split("://")[-1].strip("/")
        if len(name) > 60:
            name = name[:57] + "..."
        return self.ingest_text(clean_text, name, "url")

    def list_documents(self) -> list:
        """Lists all documents registered in databank.json (excluding chat history memory)."""
        data = self._load_data(self.db_path)
        
        chunk_counts = {}
        for chunk in data.get("chunks", []):
            doc_id = chunk.get("doc_id")
            if doc_id:
                chunk_counts[doc_id] = chunk_counts.get(doc_id, 0) + 1
            
        results = []
        for doc in data.get("documents", []):
            if doc.get("source_type") != 'chat_history':
                doc_copy = doc.copy()
                doc_copy["chunk_count"] = chunk_counts.get(doc.get("id"), 0)
                doc_copy["source_type"] = doc.get("source_type", "file")
                results.append(doc_copy)
                
        results.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return results

    def delete_document(self, doc_id: str) -> bool:
        """Removes a document and all its chunks from the databank.json file."""
        data = self._load_data(self.db_path)
        
        original_doc_count = len(data.get("documents", []))
        
        data["documents"] = [d for d in data.get("documents", []) if d.get("id") != doc_id]
        data["chunks"] = [c for c in data.get("chunks", []) if c.get("doc_id") != doc_id]
        
        self._save_data(self.db_path, data)
        return len(data["documents"]) < original_doc_count

    def delete_chat_history(self, session_id: str):
        """Deletes all chat history archives associated with the session from memories.json."""
        data = self._load_data(self.memories_path)
        
        prefix = f"chat_history_archive_{session_id}_"
        doc_ids_to_delete = [
            d.get("id") for d in data.get("documents", []) 
            if d.get("source_type") == 'chat_history' and d.get("name", "").startswith(prefix) and d.get("id")
        ]
        
        if doc_ids_to_delete:
            doc_ids_set = set(doc_ids_to_delete)
            data["documents"] = [d for d in data.get("documents", []) if d.get("id") not in doc_ids_set]
            data["chunks"] = [c for c in data.get("chunks", []) if c.get("doc_id") not in doc_ids_set]
            self._save_data(self.memories_path, data)
            
    def update_memory_document(self, doc_name: str, new_text: str) -> bool:
        """Re-chunks and re-embeds an existing memory document with distilled or updated text."""
        data = self._load_data(self.memories_path)
        matching_docs = [d for d in data["documents"] if d.get("name") == doc_name and d.get("source_type") == 'chat_history']
        if not matching_docs:
            return False
        doc = matching_docs[0]
        doc_id = doc["id"]
        
        # Remove old chunks
        data["chunks"] = [c for c in data["chunks"] if c.get("doc_id") != doc_id]
        
        # Re-chunk and embed
        model = get_embedding_model()
        new_chunks = self.chunk_text(new_text)
        if new_chunks:
            vectors = model.encode(new_chunks)
            for idx, (chunk_str, vec) in enumerate(zip(new_chunks, vectors)):
                data["chunks"].append({
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "text": chunk_str,
                    "vector": vec.tolist() if hasattr(vec, 'tolist') else list(vec)
                })
        doc["size"] = len(new_text)
        self._save_data(self.memories_path, data)
        return True

    def get_all_memories(self) -> list:
        """Retrieves all chat history archives from memories.json, including their concatenated chunk text."""
        data = self._load_data(self.memories_path)
        
        chat_docs = [
            d for d in data["documents"]
            if d.get("source_type") == 'chat_history'
        ]
        
        chat_docs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        results = []
        for doc in chat_docs:
            doc_id = doc["id"]
            doc_chunks = [c for c in data["chunks"] if c.get("doc_id") == doc_id]
            doc_chunks.sort(key=lambda x: x.get("chunk_index", 0))
            
            text = "\n".join(c["text"] for c in doc_chunks)
            
            name = doc.get("name", "")
            session_id = "default"
            if name.startswith("chat_history_archive_"):
                parts = name[len("chat_history_archive_"):].split("_")
                if len(parts) >= 2:
                    session_id = "_".join(parts[:-1])
            
            results.append({
                "id": doc_id,
                "name": name,
                "session_id": session_id,
                "timestamp": doc.get("timestamp", 0),
                "text": text
            })
            
        return results

    def get_prior_chat_histories(self, session_id: str = None, limit: int = 2) -> list:
        """Retrieves prior chat histories globally from memories.json."""
        data = self._load_data(self.memories_path)
        
        chat_docs = [
            d for d in data["documents"]
            if d.get("source_type") == 'chat_history'
        ]
        
        chat_docs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        target_docs = chat_docs[:limit]
        
        archives = []
        for doc in target_docs:
            doc_id = doc["id"]
            doc_chunks = [c for c in data["chunks"] if c.get("doc_id") == doc_id]
            doc_chunks.sort(key=lambda x: x.get("chunk_index", 0))
            
            archives.append({
                "name": doc["name"],
                "text": "\n".join(c["text"] for c in doc_chunks)
            })
            
        return archives

    def prune_chat_histories(self, session_id: str = None, keep_limit: int = 3):
        """Consolidates the oldest chat history archives when exceeding keep_limit so narrative history is preserved."""
        data = self._load_data(self.memories_path)
        
        chat_docs = [
            d for d in data["documents"]
            if d.get("source_type") == 'chat_history'
        ]
        
        # Sort chronologically with oldest documents first
        chat_docs.sort(key=lambda x: x.get("timestamp", 0))
        
        # Iteratively merge the two oldest documents until total documents match keep_limit
        while len(chat_docs) > keep_limit:
            doc_1 = chat_docs[0]
            doc_2 = chat_docs[1]
            
            # Fetch text chunks of both documents
            chunks_1 = [c["text"] for c in data["chunks"] if c.get("doc_id") == doc_1["id"]]
            chunks_2 = [c["text"] for c in data["chunks"] if c.get("doc_id") == doc_2["id"]]
            
            text_1 = " ".join(chunks_1).strip()
            text_2 = " ".join(chunks_2).strip()
            merged_text = f"{text_1} {text_2}".strip()
            
            # Remove old chunks for both documents
            to_remove_ids = {doc_1["id"], doc_2["id"]}
            data["chunks"] = [c for c in data["chunks"] if c.get("doc_id") not in to_remove_ids]
            
            # Re-chunk and embed the consolidated narrative text under doc_1
            model = get_embedding_model()
            merged_chunks = self.chunk_text(merged_text)
            if merged_chunks:
                vectors = model.encode(merged_chunks)
                for idx, (chunk_str, vec) in enumerate(zip(merged_chunks, vectors)):
                    data["chunks"].append({
                        "doc_id": doc_1["id"],
                        "chunk_index": idx,
                        "text": chunk_str,
                        "vector": vec.tolist() if hasattr(vec, 'tolist') else list(vec)
                    })
                    
            # Update doc_1 size and preserve oldest timestamp
            doc_1["size"] = len(merged_text)
            
            # Remove doc_2 from the document registry
            data["documents"] = [d for d in data["documents"] if d["id"] != doc_2["id"]]
            
            # Refresh sorted list
            chat_docs = [
                d for d in data["documents"]
                if d.get("source_type") == 'chat_history'
            ]
            chat_docs.sort(key=lambda x: x.get("timestamp", 0))
            print(f"[Data Bank] Consolidated oldest archives '{doc_1['name']}' and '{doc_2['name']}' into single progressive memory chapter.")
            
        self._save_data(self.memories_path, data)

    def purge_all(self):
        """Purges both databank.json and memories.json."""
        self._save_data(self.db_path, {"documents": [], "chunks": []})
        self._save_data(self.memories_path, {"documents": [], "chunks": []})
        print("[Data Bank] Purged all documents and vectors from databank and memories.")

    def query(self, query_text: str, top_k: int = 5, score_threshold: float = 0.25, exclude_source_type: str = None, include_source_type: str = None, token_budget: int = None, query_vector=None) -> str:
        """Queries the respective JSON vector index and returns clean contextual matching chunks."""
        # Query memories.json for chat history, otherwise query databank.json
        is_chat_history = (include_source_type == 'chat_history')
        path = self.memories_path if is_chat_history else self.db_path
        
        data = self._load_data(path)
        
        if not data.get("chunks"):
            return ""
            
        docs_map = {d.get("id"): d for d in data.get("documents", []) if d.get("id")}
        
        filtered_chunks = []
        for chunk in data.get("chunks", []):
            doc = docs_map.get(chunk.get("doc_id"))
            if not doc:
                continue
            doc_source = doc.get("source_type", "file")
            if exclude_source_type and doc_source == exclude_source_type:
                continue
            if include_source_type and doc_source != include_source_type:
                continue
            filtered_chunks.append((doc.get("name", "Document"), chunk.get("text", ""), chunk.get("vector", [])))
            
        if not filtered_chunks:
            return ""
            
        # Reuse a supplied embedding when several indexes share one query.
        if query_vector is None:
            model = get_embedding_model()
            query_vector = model.encode(query_text)
        
        # Norm of query vector
        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            return ""
            
        results = []
        for doc_name, chunk_text, vector in filtered_chunks:
            chunk_vector = np.array(vector)
            chunk_norm = np.linalg.norm(chunk_vector)
            if chunk_norm == 0:
                continue
                
            # Compute cosine similarity
            similarity = np.dot(query_vector, chunk_vector) / (query_norm * chunk_norm)
            
            if similarity >= score_threshold:
                results.append((similarity, doc_name, chunk_text))
                
        results.sort(key=lambda x: x[0], reverse=True)
        top_results = results[:top_k]
        
        if not top_results:
            return ""
        
        # Enforce token budget (approximate: 1 token ≈ 4 chars)
        if token_budget:
            budget_chars = token_budget * 4
            budgeted = []
            char_count = 0
            for result in top_results:
                result_chars = len(result[2])
                if char_count + result_chars > budget_chars and budgeted:
                    break
                budgeted.append(result)
                char_count += result_chars
            top_results = budgeted
        
        # Diagnostic logging
        best_score = top_results[0][0] if top_results else 0
        best_source = top_results[0][1] if top_results else "none"
        context_type = "memory" if is_chat_history else "knowledge"
        print(f"[RAG] {context_type}: {len(top_results)} chunks retrieved (best: {best_score:.3f} from '{best_source}')", flush=True)
            
        formatted_context = []
        if is_chat_history:
            for score, doc_name, text in top_results:
                formatted_context.append(text.strip())
            return "\n\n---\n\n".join(formatted_context)
        else:
            for idx, (score, doc_name, text) in enumerate(top_results):
                formatted_context.append(f"[{idx+1}] Source: {doc_name} (Similarity: {score:.2f})\n{text.strip()}")
            return "\n\n".join(formatted_context)
