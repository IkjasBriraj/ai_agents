"""
AI Guide Backend
A FastAPI-based backend for the AI Guide assistant
"""

from .api import create_guide_router, create_guide_app
from .config import AIGuideConfig
from .models import ChatMessage, GuideChatRequest, GuideChatChunk

__version__ = "1.0.0"
__all__ = [
    "create_guide_router",
    "create_guide_app",
    "AIGuideConfig",
    "ChatMessage",
    "GuideChatRequest",
    "GuideChatChunk",
]

# Made with Bob
