import os
import json
import numpy as np
import httpx
from typing import List, Dict, Any, Tuple
from .config import AGENT_WORKSPACE_DIR, is_allowed_extension

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
            print(f"Error getting embedding: {e}")
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
