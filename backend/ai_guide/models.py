"""
AI Guide Backend - Data Models
Pydantic models for request/response validation
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    timestamp: Optional[int] = Field(None, description="Unix timestamp in milliseconds")


class GuideChatRequest(BaseModel):
    """Request model for chat endpoint"""
    messages: List[ChatMessage] = Field(..., description="Conversation history")
    page_context: str = Field(..., description="Current page/section context")


class GuideChatChunk(BaseModel):
    """Streaming response chunk model"""
    content: Optional[str] = Field(default=None, description="Content chunk")
    error: Optional[str] = Field(default=None, description="Error message if any")
    done: Optional[bool] = Field(default=False, description="Whether streaming is complete")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    model_provider: str = Field(..., description="LLM provider")
    model_name: str = Field(..., description="LLM model name")
    message: Optional[str] = Field(default=None, description="Additional status message")

# Made with Bob
