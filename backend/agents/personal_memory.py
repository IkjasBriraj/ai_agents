"""
Personal Knowledge Journal & RAG Long-Term Memory Service
Persists user preferences, facts, and project notes across sessions.
Provides semantic retrieval and real-time streaming notifications when memories are saved.
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from database.db import SessionLocal
    from database.models import PersonalMemoryModel
except ImportError:
    try:
        from backend.database.db import SessionLocal
        from backend.database.models import PersonalMemoryModel
    except ImportError:
        SessionLocal = None
        PersonalMemoryModel = None

from .vector_store import LocalVectorStore, OllamaEmbeddings
from .session_context import current_agent_context

logger = logging.getLogger(__name__)

MEMORY_VECTOR_STORE_PATH = os.path.join(os.path.dirname(__file__), "personal_memory_store.json")

class PersonalMemoryManager:
    """Manages persistent personal memories, user preferences, and semantic recall."""
    
    def __init__(self, storage_path: str = MEMORY_VECTOR_STORE_PATH):
        self.vector_store = LocalVectorStore(storage_path)
        self.embedder = OllamaEmbeddings()

    def _notify_user_saving(self, memory_data: Dict[str, Any]):
        """Stream an interactive UI notification when a memory is being saved so user sees it in real-time."""
        try:
            ctx = current_agent_context.get()
            if ctx and "queue" in ctx and "loop" in ctx:
                queue = ctx["queue"]
                loop = ctx["loop"]
                title = memory_data.get("title") or memory_data.get("category", "preference").title()
                content = memory_data.get("content", "")
                
                # 1. Emit dedicated memory_saved event for custom UI badges / toasts
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "memory_saved",
                        "memory": memory_data,
                        "done": False
                    }
                )
                
                # 2. Also stream visible inline thinking notification
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "thinking",
                        "content": f"\n🧠 **[Knowledge Journal]** Saved to memory: *\"{content}\"*\n"
                    }
                )
        except Exception as e:
            logger.debug(f"Could not notify user of memory saving: {e}")

    def save_memory(
        self,
        content: str,
        category: str = "preference",
        title: str = "",
        tags: Optional[List[str]] = None,
        broadcast: bool = True
    ) -> Dict[str, Any]:
        """Save a new memory to database and vector store with user notification."""
        content = content.strip()
        if not content:
            return {"error": "Memory content cannot be empty."}

        category = category.lower().strip()
        if category not in ["preference", "personal_fact", "project_note", "contact", "system"]:
            category = "preference"

        if not title:
            # Generate short title from first 6 words
            words = content.split()
            title = " ".join(words[:6]) + ("..." if len(words) > 6 else "")

        tags = tags or []
        created_id = None
        created_at_str = datetime.utcnow().isoformat()

        if SessionLocal and PersonalMemoryModel:
            db = SessionLocal()
            try:
                mem = PersonalMemoryModel(
                    category=category,
                    title=title,
                    content=content,
                    tags=tags,
                    created_at=datetime.utcnow()
                )
                db.add(mem)
                db.commit()
                db.refresh(mem)
                created_id = mem.id
                created_at_str = mem.created_at.isoformat()
            except Exception as e:
                db.rollback()
                logger.error(f"Error saving memory to DB: {e}")
            finally:
                db.close()

        # Generate embedding and store in vector store
        try:
            emb = self.embedder.embed_text(content)
            self.vector_store.add_document(
                text=content,
                metadata={
                    "id": created_id,
                    "title": title,
                    "category": category,
                    "tags": tags,
                    "created_at": created_at_str
                },
                embedding=emb
            )
        except Exception as ve:
            logger.warning(f"Could not embed memory: {ve}")

        memory_dict = {
            "id": created_id,
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "created_at": created_at_str
        }

        if broadcast:
            self._notify_user_saving(memory_dict)

        return memory_dict

    def search_memories(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Find relevant memories using semantic similarity and keyword matching."""
        if not query or not query.strip():
            return []

        results = []
        # 1. Semantic search
        try:
            query_emb = self.embedder.embed_text(query)
            if query_emb:
                vector_matches = self.vector_store.query(query_emb, k=top_k)
                for score, doc in vector_matches:
                    if score > 0.45:  # Similarity threshold
                        meta = doc.get("metadata", {})
                        results.append({
                            "id": meta.get("id"),
                            "title": meta.get("title"),
                            "content": doc.get("text"),
                            "category": meta.get("category", "preference"),
                            "score": float(score)
                        })
        except Exception as e:
            logger.debug(f"Vector search failed in personal memories: {e}")

        # 2. If vector search returned few results, fallback to database keyword search
        if len(results) < 2 and SessionLocal and PersonalMemoryModel:
            db = SessionLocal()
            try:
                words = [w.lower() for w in re.findall(r'\b\w{3,}\b', query) if w not in ["what", "where", "when", "that", "this", "with", "have"]]
                all_mems = db.query(PersonalMemoryModel).order_by(PersonalMemoryModel.created_at.desc()).limit(30).all()
                for m in all_mems:
                    content_lower = m.content.lower()
                    if any(w in content_lower for w in words):
                        if not any(r.get("id") == m.id for r in results):
                            results.append({
                                "id": m.id,
                                "title": m.title,
                                "content": m.content,
                                "category": m.category,
                                "score": 0.5
                            })
                            if len(results) >= top_k:
                                break
            except Exception as dbe:
                logger.error(f"Keyword search failed: {dbe}")
            finally:
                db.close()

        return results[:top_k]

    def list_memories(self, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List all personal memories, optionally filtered by category."""
        if not SessionLocal or not PersonalMemoryModel:
            # Fallback to vector store json data
            docs = self.vector_store.data
            items = []
            for d in docs:
                m = d.get("metadata", {})
                if category and m.get("category") != category:
                    continue
                items.append({
                    "id": m.get("id"),
                    "title": m.get("title", ""),
                    "content": d.get("text", ""),
                    "category": m.get("category", "preference"),
                    "tags": m.get("tags", []),
                    "created_at": m.get("created_at", "")
                })
            return items[-limit:]

        db = SessionLocal()
        try:
            q = db.query(PersonalMemoryModel)
            if category:
                q = q.filter(PersonalMemoryModel.category == category)
            mems = q.order_by(PersonalMemoryModel.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": m.id,
                    "title": m.title,
                    "content": m.content,
                    "category": m.category,
                    "tags": m.tags or [],
                    "created_at": m.created_at.isoformat() if m.created_at else ""
                }
                for m in mems
            ]
        finally:
            db.close()

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory by its ID."""
        success = False
        if SessionLocal and PersonalMemoryModel:
            db = SessionLocal()
            try:
                mem = db.query(PersonalMemoryModel).filter(PersonalMemoryModel.id == memory_id).first()
                if mem:
                    db.delete(mem)
                    db.commit()
                    success = True
            except Exception as e:
                db.rollback()
                logger.error(f"Error deleting memory from DB: {e}")
            finally:
                db.close()

        # Also purge from vector store
        self.vector_store.data = [
            item for item in self.vector_store.data
            if item.get("metadata", {}).get("id") != memory_id
        ]
        self.vector_store._save_store()
        return success

    def get_relevant_context_prompt(self, user_request: str) -> str:
        """Retrieve relevant memories and format into a system prompt segment."""
        matches = self.search_memories(user_request, top_k=3)
        if not matches:
            return ""

        lines = ["\n[USER PERSONAL KNOWLEDGE & PREFERENCES (PERSISTENT MEMORY)]:"]
        for m in matches:
            cat = m.get("category", "fact").upper()
            lines.append(f"- ({cat}) {m.get('content')}")
        lines.append("Honor these personal preferences and context in your response.\n")
        return "\n".join(lines)

    def auto_extract_and_save_if_relevant(self, user_request: str) -> Optional[Dict[str, Any]]:
        """Inspect if the user explicitly asked to remember something and save it automatically."""
        req_lower = user_request.lower().strip()
        
        remember_triggers = [
            r'remember\s+(?:that\s+)?(.+)',
            r'keep\s+in\s+mind\s+(?:that\s+)?(.+)',
            r'note\s+(?:down\s+)?(?:that\s+)?(.+)',
            r'save\s+(?:this\s+)?(?:to\s+memory|in\s+memory|to\s+your\s+journal)[:\s]*(.+)',
            r'my\s+preference\s+is\s+(.+)',
            r'i\s+prefer\s+(.+)',
        ]

        for pat in remember_triggers:
            match = re.search(pat, req_lower)
            if match:
                extracted = match.group(1).strip()
                # Clean punctuation
                extracted = re.sub(r'[\.\!\?]+$', '', extracted).strip()
                if len(extracted) > 4:
                    category = "preference" if ("prefer" in req_lower or "like" in req_lower or "always" in req_lower) else "personal_fact"
                    title = "User Preference" if category == "preference" else "Personal Fact"
                    return self.save_memory(
                        content=extracted,
                        category=category,
                        title=title,
                        broadcast=True
                    )
        return None

# Singleton instance
personal_memory = PersonalMemoryManager()
