import os
import json
import numpy as np
import httpx
from typing import List, Dict, Any, Tuple
from .config import AGENT_WORKSPACE_DIR, is_allowed_extension

import re
import math
import hashlib
import logging

logger = logging.getLogger(__name__)

def _local_hash_embedding(text: str, dim: int = 128) -> List[float]:
    """Deterministic local semantic hash embedding fallback when Ollama embeddings are unavailable."""
    vec = [0.0] * dim
    words = re.findall(r'\w+', text.lower())
    for w in words:
        h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16) % dim
        vec[h] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec

class OllamaEmbeddings:
    """Utility to get embeddings from local Ollama server with deterministic offline fallback."""
    def __init__(self, model_name: Optional[str] = None, base_url: str = "http://localhost:11434"):
        env_embed_model = os.environ.get("OLLAMA_EMBED_MODEL", "").strip() or os.environ.get("EMBED_MODEL", "").strip()
        self.model_name = model_name or env_embed_model or None
        self.base_url = base_url
        self._checked_model = False
        self._active_model: Optional[str] = None

    def _resolve_model(self) -> Optional[str]:
        """Resolve a dedicated embedding model, avoiding loading heavy LLMs in the background."""
        if self._checked_model:
            return self._active_model

        self._checked_model = True

        if self.model_name:
            self._active_model = self.model_name
            return self._active_model

        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                embed_keywords = ["embed", "minilm", "bge-", "arctic-embed", "mxbai"]
                for m in models:
                    m_lower = m.lower()
                    if any(kw in m_lower for kw in embed_keywords):
                        self._active_model = m
                        return self._active_model
        except Exception:
            pass

        self._active_model = None
        return None

    def embed_text(self, text: str) -> List[float]:
        """Get embedding for a piece of text."""
        if not text or not text.strip():
            return [0.0] * 128

        active_model = self._resolve_model()
        if active_model:
            try:
                resp = httpx.post(
                    f"{self.base_url}/api/embed",
                    json={"model": active_model, "input": text},
                    timeout=5.0
                )
                if resp.status_code == 200:
                    embs = resp.json().get("embeddings", [])
                    if embs and len(embs) > 0 and len(embs[0]) > 0:
                        return embs[0]

                response = httpx.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": active_model, "prompt": text},
                    timeout=5.0
                )
                if response.status_code == 200:
                    emb = response.json().get("embedding", [])
                    if emb:
                        return emb
            except Exception as e:
                logger.debug(f"Error getting embedding from Ollama: {e}")

        return _local_hash_embedding(text)

class LocalVectorStore:
    """A simple, file-based vector store using numpy for cosine similarity."""
    def __init__(self, storage_path: str = "vector_store.json"):
        self.storage_path = storage_path
        self.data = self._load_store()

    def _load_store(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading vector store: {e}")
        return []

    def _save_store(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving vector store: {e}")

    def add_document(self, text: str, metadata: Dict[str, Any], embedding: List[float]):
        """Add a document embedding to the store."""
        self.data.append({
            "text": text,
            "metadata": metadata,
            "embedding": embedding
        })
        self._save_store()

    def query(self, query_embedding: List[float], k: int = 3) -> List[Tuple[float, Dict[str, Any]]]:
        """Find top K most similar documents using cosine similarity."""
        if not self.data:
            return []

        results = []
        query_vec = np.array(query_embedding)

        for item in self.data:
            doc_vec = np.array(item["embedding"])
            if len(doc_vec) != len(query_vec):
                continue  # dimension mismatch protection
            # Cosine Similarity: (A . B) / (||A|| * ||B||)
            norm_q = np.linalg.norm(query_vec)
            norm_d = np.linalg.norm(doc_vec)
            if norm_q == 0 or norm_d == 0:
                similarity = 0.0
            else:
                similarity = np.dot(query_vec, doc_vec) / (norm_q * norm_d)

            results.append((similarity, item))

        # Sort by similarity descending
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:k]

    def clear(self):
        self.data = []
        self._save_store()

def index_workspace(embedder: OllamaEmbeddings, store: LocalVectorStore):
    """Index the entire agent workspace."""
    print(f"Indexing workspace: {AGENT_WORKSPACE_DIR}...")
    store.clear()

    for root, _, files in os.walk(AGENT_WORKSPACE_DIR):
        for file in files:
            full_path = os.path.join(root, file)
            if not is_allowed_extension(full_path):
                continue

            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Chunking: Split by paragraphs or every 500 chars
                chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]

                for i, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    embedding = embedder.embed_text(chunk)
                    if embedding:
                        store.add_document(
                            text=chunk,
                            metadata={"path": full_path, "chunk": i},
                            embedding=embedding
                        )
            except Exception as e:
                print(f"Error indexing {full_path}: {e}")

    print("Indexing complete.")

def query_workspace(query: str, embedder: OllamaEmbeddings, store: LocalVectorStore, k: int = 3) -> str:
    """Search the indexed workspace for relevant content."""
    query_embedding = embedder.embed_text(query)
    if not query_embedding:
        return "Error: Could not generate embedding for query."

    results = store.query(query_embedding, k=k)
    if not results:
        return "No relevant content found in the workspace."

    output = "Relevant context found in workspace:\n\n"
    for score, item in results:
        path = item["metadata"]["path"]
        rel_path = os.path.relpath(path, AGENT_WORKSPACE_DIR)
        output += f"[Score: {score:.4f}] File: {rel_path}\nContent: {item['text']}\n---\n"

    return output
