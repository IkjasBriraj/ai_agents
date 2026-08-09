import os
import json
import numpy as np
import httpx
import re
import math
import hashlib
import logging
from typing import List, Dict, Any, Tuple, Optional, Union
try:
    from agents.config import AGENT_WORKSPACE_DIR, is_allowed_extension
except ImportError:
    try:
        from .config import AGENT_WORKSPACE_DIR, is_allowed_extension
    except ImportError:
        AGENT_WORKSPACE_DIR = r"D:\learning\code\website"
        def is_allowed_extension(filename: str) -> bool:
            return True

logger = logging.getLogger(__name__)

class OllamaEmbeddings:
    """Utility to get embeddings from local Ollama server."""
    def __init__(self, model_name: str = "granite4.1:8b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    def embed_text(self, text: str) -> List[float]:
        """Get embedding for a piece of text."""
        try:
            response = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json().get("embedding", [])
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return []

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
                logger.error(f"Error loading vector store: {e}")
        return []

    def _save_store(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")

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

class BM25Index:
    """Simple, pure-Python BM25 keyword index implementation."""
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.doc_term_freqs: Dict[str, Dict[str, int]] = {}
        self.docs: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        self.avg_dl = 0.0
        self.num_docs = 0
        self.stop_words = {"the", "is", "in", "and", "to", "of", "a", "for", "with", "on", "as", "by", "at", "an", "this", "that", "it"}

    def tokenize(self, text: str) -> List[str]:
        """Lowercase, split on non-alphanumeric, filter stop words"""
        tokens = re.split(r'[^a-zA-Z0-9]', text.lower())
        return [t for t in tokens if t and t not in self.stop_words]

    def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any]) -> None:
        if doc_id in self.docs:
            return
        
        tokens = self.tokenize(text)
        length = len(tokens)
        self.doc_lengths[doc_id] = length
        self.docs[doc_id] = (text, metadata)
        self.num_docs += 1
        self.avg_dl = sum(self.doc_lengths.values()) / max(1, self.num_docs)

        term_freqs = {}
        for token in tokens:
            term_freqs[token] = term_freqs.get(token, 0) + 1
            
        self.doc_term_freqs[doc_id] = term_freqs

        for token in term_freqs:
            self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

    def search(self, query: str, top_k: int = 5) -> List[Tuple[float, Dict[str, Any]]]:
        query_tokens = self.tokenize(query)
        scores: Dict[str, float] = {}

        for token in query_tokens:
            if token not in self.doc_freqs:
                continue
            df = self.doc_freqs[token]
            idf = math.log(1 + (self.num_docs - df + 0.5) / (df + 0.5))
            
            for doc_id, term_freqs in self.doc_term_freqs.items():
                if token in term_freqs:
                    tf = term_freqs[token]
                    dl = self.doc_lengths[doc_id]
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (dl / self.avg_dl))
                    score = idf * (numerator / denominator)
                    scores[doc_id] = scores.get(doc_id, 0.0) + score

        results = []
        for doc_id, score in scores.items():
            results.append((score, {"text": self.docs[doc_id][0], "metadata": self.docs[doc_id][1], "id": doc_id}))
            
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]


class HybridCodeStore:
    """Combines vector embeddings + sparse keyword search + file hash tracking"""
    def __init__(self, storage_path: str = "vector_store.json", embedder: Optional[OllamaEmbeddings] = None):
        self.dense_store = LocalVectorStore(storage_path)
        self.sparse_index = BM25Index()
        self.embedder = embedder
        self.file_hashes: Dict[str, str] = {}
        self.doc_counter = 0

        for item in self.dense_store.data:
            doc_id = f"doc_{self.doc_counter}"
            self.sparse_index.add_document(doc_id, item["text"], item["metadata"])
            self.doc_counter += 1

    def is_file_changed(self, file_path: str) -> bool:
        try:
            with open(file_path, 'rb') as f:
                current_hash = hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error reading file for hash: {e}")
            return True

        if file_path not in self.file_hashes or self.file_hashes[file_path] != current_hash:
            self.file_hashes[file_path] = current_hash
            return True
        return False

    def add_document(self, text: str, metadata: Dict[str, Any], embedding: Optional[List[float]] = None):
        if embedding is None and self.embedder:
            embedding = self.embedder.embed_text(text)
        
        if not embedding:
            embedding = []
            
        self.dense_store.add_document(text, metadata, embedding)
        doc_id = f"doc_{self.doc_counter}"
        self.sparse_index.add_document(doc_id, text, metadata)
        self.doc_counter += 1

    def hybrid_query(self, query: str, k: int = 5, alpha: float = 0.5) -> List[Tuple[float, Dict[str, Any]]]:
        dense_results = []
        if self.embedder:
            query_embedding = self.embedder.embed_text(query)
            if query_embedding:
                dense_results = self.dense_store.query(query_embedding, k=k*2)

        sparse_results = self.sparse_index.search(query, top_k=k*2)

        dense_max = max((score for score, _ in dense_results), default=1.0) or 1.0
        dense_min = min((score for score, _ in dense_results), default=0.0)
        
        sparse_max = max((score for score, _ in sparse_results), default=1.0) or 1.0
        sparse_min = min((score for score, _ in sparse_results), default=0.0)

        combined_scores: Dict[str, Tuple[float, Dict[str, Any]]] = {}

        def get_id(meta):
            return f"{meta.get('path', '')}_{meta.get('chunk', '')}"

        for score, item in dense_results:
            n_score = (score - dense_min) / (dense_max - dense_min) if dense_max > dense_min else score / dense_max
            doc_key = get_id(item["metadata"])
            combined_scores[doc_key] = (alpha * n_score, item)

        for score, item in sparse_results:
            n_score = (score - sparse_min) / (sparse_max - sparse_min) if sparse_max > sparse_min else score / sparse_max
            doc_key = get_id(item["metadata"])
            if doc_key in combined_scores:
                prev_score, prev_item = combined_scores[doc_key]
                combined_scores[doc_key] = (prev_score + (1 - alpha) * n_score, prev_item)
            else:
                combined_scores[doc_key] = ((1 - alpha) * n_score, item)

        results = list(combined_scores.values())
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:k]

def index_workspace(embedder: OllamaEmbeddings, store: Union[LocalVectorStore, HybridCodeStore]):
    """Index the entire agent workspace."""
    print(f"Indexing workspace: {AGENT_WORKSPACE_DIR}...")
    
    if isinstance(store, HybridCodeStore):
        store.dense_store.clear()
        store.sparse_index = BM25Index()
        store.doc_counter = 0
    else:
        store.clear()

    for root, _, files in os.walk(AGENT_WORKSPACE_DIR):
        for file in files:
            full_path = os.path.join(root, file)
            if not is_allowed_extension(full_path):
                continue

            if isinstance(store, HybridCodeStore) and not store.is_file_changed(full_path):
                continue

            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Chunking: Split by paragraphs or every 500 chars
                chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]

                for i, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                        
                    if isinstance(store, HybridCodeStore):
                        store.add_document(
                            text=chunk,
                            metadata={"path": full_path, "chunk": i}
                        )
                    else:
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

def query_workspace(query: str, embedder: OllamaEmbeddings, store: Union[LocalVectorStore, HybridCodeStore], k: int = 3) -> str:
    """Search the indexed workspace for relevant content."""
    
    if isinstance(store, HybridCodeStore):
        results = store.hybrid_query(query, k=k)
    else:
        query_embedding = embedder.embed_text(query)
        if not query_embedding:
            return "Error: Could not generate embedding for query."
        results = store.query(query_embedding, k=k)

    if not results:
        return "No relevant content found in the workspace."

    output = "Relevant context found in workspace:\n\n"
    for score, item in results:
        meta = item.get("metadata", {})
        path = meta.get("path", "Unknown")
        text = item.get("text", "")
        
        rel_path = os.path.relpath(path, AGENT_WORKSPACE_DIR) if path != "Unknown" else "Unknown"
        output += f"[Score: {score:.4f}] File: {rel_path}\nContent: {text}\n---\n"

    return output
