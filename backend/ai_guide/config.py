"""
AI Guide Backend - Configuration
Configuration management for the AI Guide backend
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class AIGuideConfig:
    """Configuration for AI Guide backend"""
    
    # LLM Configuration
    model_provider: str = "ollama"
    """LLM provider (ollama, openai, anthropic, azure, etc.)"""
    
    model_name: str = "qwen3.5:9b"
    """Model name to use"""
    
    api_base: Optional[str] = "http://localhost:11434"
    """API base URL for the LLM provider"""
    
    api_key: Optional[str] = None
    """API key for authentication (if required)"""
    
    # Prompt Configuration
    system_prompt_template: str = """You are an AI assistant for the {context} section of the application.
Your goal is to help users understand and navigate this part of the application.

When users first open the chat or switch pages, provide a concise summary (2-3 sentences) of what they can do here.

Keep your responses professional, helpful, and concise. Use Markdown for formatting when appropriate.
"""
    """System prompt template with {context} placeholder"""
    
    context_labels: Optional[Dict[str, str]] = None
    """Mapping of context keys to user-friendly labels"""
    
    # API Configuration
    enable_cors: bool = True
    """Enable CORS middleware"""
    
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    """Allowed CORS origins"""
    
    rate_limit: Optional[int] = None
    """Rate limit in requests per minute (None = no limit)"""
    
    # Streaming Configuration
    stream_timeout: int = 30
    """Timeout for streaming responses in seconds"""
    
    max_tokens: int = 2000
    """Maximum tokens to generate"""
    
    temperature: float = 0.7
    """Temperature for response generation"""
    
    # Logging
    log_level: str = "INFO"
    """Logging level (DEBUG, INFO, WARNING, ERROR)"""
    
    def get_system_prompt(self, context: str) -> str:
        """
        Get the system prompt for a given context
        
        Args:
            context: The current page/section context
            
        Returns:
            Formatted system prompt
        """
        # Get context label if available
        if self.context_labels and context in self.context_labels:
            context_label = self.context_labels[context]
        else:
            context_label = context
        
        return self.system_prompt_template.format(context=context_label)
    
    def get_litellm_params(self) -> Dict:
        """
        Get parameters for LiteLLM completion
        
        Returns:
            Dictionary of LiteLLM parameters
        """
        params = {
            "model": f"{self.model_provider}/{self.model_name}",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        
        if self.api_base:
            params["api_base"] = self.api_base
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        return params

# Made with Bob
