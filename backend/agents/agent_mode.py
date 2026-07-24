import json
import httpx
from typing import AsyncGenerator, Dict, Any, List, Optional
import logging
import os

from .claude_code_service import get_claude_code_service
from .config import is_safe_path, CLAUDE_CODE_ALLOWED_TOOLS, CLAUDE_CODE_MAX_TURNS

logger = logging.getLogger(__name__)

class AgentModeOrchestrator:
    """Agent Mode: Ollama brain + Claude Code tools for Workspace Explorer"""
    
    def __init__(self, model_name="gemma4:31b-cloud", ollama_base_url="http://localhost:11434"):
        self.model_name = model_name
        self.ollama_base_url = ollama_base_url
        self.claude_service = get_claude_code_service()
        self.conversations: Dict[str, List[Dict[str, str]]] = {}  # session_id -> list of messages
    
    def _build_system_prompt(self, cwd: str, file_path: Optional[str] = None, file_content: Optional[str] = None) -> str:
        prompt = (
            "You are an advanced AI developer assistant with access to the user's workspace. "
            "You can analyze code, suggest improvements, generate code, explain what files do, and perform file operations.\n"
            f"Current working directory: {cwd}\n"
        )
        if file_path:
            prompt += f"\nActive file: {file_path}\n"
            if file_content:
                prompt += f"Active file content:\n```\n{file_content}\n```\n"
        
        prompt += (
            "\nIf you are asked to perform an action on a file, clearly state your intent. "
            "If the tools (like Claude Code) are available, they will be invoked automatically based on your analysis. "
            "When you need to do file operations, describe what you want to do."
        )
        return prompt

    async def process_chat(self, prompt: str, cwd: str, 
                           file_path: str = None, 
                           file_content: str = None,
                           session_id: str = "default") -> AsyncGenerator[Dict[str, Any], None]:
        """Process a chat message - yields SSE event dicts"""
        
        # Security check for file path if provided
        if file_path and not is_safe_path(file_path):
            yield {"type": "error", "content": f"Path is not safe: {file_path}"}
            return
            
        claude_available = await self.claude_service.is_available()
        
        # Update history
        if session_id not in self.conversations:
            system_msg = self._build_system_prompt(cwd, file_path, file_content)
            self.conversations[session_id] = [{"role": "system", "content": system_msg}]
            
        self.conversations[session_id].append({"role": "user", "content": prompt})
        
        # First, call Ollama to reason about the request
        yield {"type": "thinking", "content": "Thinking..."}
        
        full_response = ""
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("POST", f"{self.ollama_base_url}/api/chat", json={
                    "model": self.model_name,
                    "messages": self.conversations[session_id],
                    "stream": True
                }) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                full_response += token
                                yield {"type": "text", "content": token}
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            yield {"type": "error", "content": f"Failed to call Ollama: {str(e)}"}
            return
            
        self.conversations[session_id].append({"role": "assistant", "content": full_response})
        
        # If Claude Code is available, we might want to delegate some execution to it
        if claude_available and any(kw in full_response.lower() for kw in ["i will edit", "i'll modify", "i'll change", "let me update", "refactor", "run command", "create"]):
            yield {"type": "thinking", "content": "Delegating to Claude Code..."}
            try:
                # We pass the user's prompt to Claude Code to actually perform the operation
                async for event in self.claude_service.execute(
                    prompt=f"The user wants to: {prompt}\nContext: {full_response}",
                    cwd=cwd,
                    allowed_tools=CLAUDE_CODE_ALLOWED_TOOLS,
                    max_turns=CLAUDE_CODE_MAX_TURNS
                ):
                    yield event
            except Exception as e:
                yield {"type": "error", "content": f"Claude Code execution failed: {str(e)}"}
                
        yield {"type": "complete", "content": full_response}
    
    async def quick_action(self, action: str, file_path: str, 
                           file_content: str, cwd: str,
                           session_id: str = "default") -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a predefined quick action on a file"""
        prompts = {
            "explain": "Analyze and explain what this file does. Break down its purpose, key functions/classes, dependencies, and how it fits in the project.",
            "find_bugs": "Analyze this file for bugs, security vulnerabilities, edge cases, and potential issues. For each issue found, explain the problem and suggest a fix.",
            "refactor": "Refactor this file to improve code quality. Apply best practices, improve naming, reduce complexity, and enhance readability. Show the specific changes.",
            "add_tests": "Generate comprehensive unit tests for this file. Use the appropriate testing framework for the language. Cover edge cases and important scenarios.",
            "document": "Add comprehensive documentation to this file. Add/improve docstrings, inline comments for complex logic, and a file-level description.",
            "fix_errors": "Find and fix all errors in this file - syntax errors, type errors, logic errors, and lint issues. Show each fix.",
            "optimize": "Optimize this file for performance. Identify bottlenecks, suggest algorithmic improvements, and optimize resource usage.",
            "find_related": "Find all files related to this one - imports, dependents, test files, and configuration files that reference it."
        }
        
        prompt = prompts.get(action)
        if not prompt:
            yield {"type": "error", "content": f"Unknown action: {action}"}
            return
            
        async for event in self.process_chat(
            prompt=prompt, 
            cwd=cwd, 
            file_path=file_path, 
            file_content=file_content,
            session_id=session_id
        ):
            yield event
    
    def get_history(self, session_id: str) -> list:
        return self.conversations.get(session_id, [])
    
    def clear_history(self, session_id: str):
        self.conversations.pop(session_id, None)

_orchestrator = None
def get_agent_mode_orchestrator(model_name: str, ollama_base_url: str) -> AgentModeOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentModeOrchestrator(model_name, ollama_base_url)
    return _orchestrator
