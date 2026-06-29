"""
Multi-Agent Memory Manager
Stores and formats conversation history for the multi-agent system.
Back-end SQLite persistence using SQLAlchemy.
"""

from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from database.db import SessionLocal
from database.models import ChatMessageModel


class MultiAgentMemory:
    """
    SQLAlchemy-backed store for session-specific conversation history
    """
    
    def get_messages(self, session_id: str) -> List[BaseMessage]:
        """Get all messages for a given session ID from SQLite"""
        session = SessionLocal()
        try:
            db_msgs = session.query(ChatMessageModel).filter(
                ChatMessageModel.session_id == session_id
            ).order_by(ChatMessageModel.timestamp.asc()).all()
            
            messages = []
            for msg in db_msgs:
                if msg.role == "human":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "ai":
                    messages.append(AIMessage(content=msg.content))
                elif msg.role == "system":
                    messages.append(SystemMessage(content=msg.content))
            return messages
        except Exception as e:
            print(f"Error fetching memory for session {session_id}: {e}")
            return []
        finally:
            session.close()
        
    def add_message(self, session_id: str, message: BaseMessage):
        """Add a single message to a session ID's history in SQLite"""
        session = SessionLocal()
        try:
            role = "human" if isinstance(message, HumanMessage) else "ai"
            if isinstance(message, SystemMessage):
                role = "system"
                
            db_msg = ChatMessageModel(
                session_id=session_id,
                role=role,
                content=message.content
            )
            session.add(db_msg)
            session.commit()
        except Exception as e:
            print(f"Error adding message to session {session_id}: {e}")
        finally:
            session.close()
        
    def clear(self, session_id: str):
        """Clear all messages for a session ID in SQLite"""
        session = SessionLocal()
        try:
            session.query(ChatMessageModel).filter(
                ChatMessageModel.session_id == session_id
            ).delete()
            session.commit()
        except Exception as e:
            print(f"Error clearing memory for session {session_id}: {e}")
        finally:
            session.close()
        
    def format_history(self, session_id: str) -> str:
        """Format the session history as a string suitable for LLM prompts"""
        messages = self.get_messages(session_id)
        if not messages:
            return ""
            
        formatted = []
        for msg in messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)


# Global instance of multi-agent memory
multi_agent_memory = MultiAgentMemory()
