import asyncio
import json
import os
from typing import AsyncGenerator, Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ClaudeCodeService:
    """Wraps Claude Code CLI for agentic file operations"""
    
    def __init__(self):
        self._available = None  # Lazy check
    
    async def is_available(self) -> bool:
        """Check if 'claude' CLI is installed and accessible"""
        if self._available is not None:
            return self._available
            
        try:
            # We use 'claude --version' or equivalent to check if it's there
            process = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            self._available = (process.returncode == 0)
        except Exception:
            self._available = False
            
        return self._available
    
    async def execute(self, prompt: str, cwd: str, 
                      allowed_tools: list = None,
                      max_turns: int = 10,
                      output_format: str = "stream-json") -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a Claude Code prompt and stream results"""
        is_avail = await self.is_available()
        if not is_avail:
            raise RuntimeError("Claude Code CLI ('claude') is not available on this system.")
            
        cmd = ["claude", "-p", prompt, "--output-format", output_format, "--max-turns", str(max_turns)]
        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])
            
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            
            # Read stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                    
                line_str = line.decode('utf-8').strip()
                if line_str:
                    try:
                        # Parse the json output if it's stream-json
                        data = json.loads(line_str)
                        yield data
                    except json.JSONDecodeError:
                        # In case of non-JSON output, wrap it in a text event
                        yield {"type": "text", "content": line_str}
            
            await process.wait()
        except Exception as e:
            logger.error(f"Error executing claude code: {e}")
            yield {"type": "error", "content": str(e)}
            
    async def _run_command(self, prompt: str, tools: List[str], max_turns: int, cwd: str) -> Dict[str, Any]:
        """Helper to run a command and collect output"""
        events = []
        try:
            async for event in self.execute(prompt, cwd, allowed_tools=tools, max_turns=max_turns):
                events.append(event)
            return {"status": "success", "events": events}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def read_file(self, file_path: str, cwd: str) -> dict:
        """Use Claude Code to read a file - returns {content, lines}"""
        prompt = f"Read the file at {file_path} and return its full contents"
        return await self._run_command(prompt, ["Read"], 1, cwd)
    
    async def edit_file(self, file_path: str, instructions: str, cwd: str) -> dict:
        """Use Claude Code to edit a file based on instructions"""
        return await self._run_command(instructions, ["Read", "Edit", "MultiEdit"], 5, cwd)
    
    async def search_files(self, path: str, query: str, cwd: str) -> dict:
        """Search files using Claude Code's Grep and Glob tools"""
        prompt = f"Search for {query} in {path}"
        return await self._run_command(prompt, ["Grep", "Glob", "LS"], 3, cwd)
    
    async def run_bash(self, command: str, cwd: str) -> dict:
        """Run a bash command through Claude Code"""
        prompt = f"Run: {command}"
        return await self._run_command(prompt, ["Bash"], 1, cwd)
    
    async def analyze_codebase(self, path: str, cwd: str) -> dict:
        """Analyze a codebase/file structure"""
        prompt = f"Analyze the codebase at {path}. Explain its structure and key components."
        return await self._run_command(prompt, ["Read", "Glob", "Grep", "LS"], 5, cwd)

# Singleton
_claude_service = None
def get_claude_code_service() -> ClaudeCodeService:
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeCodeService()
    return _claude_service
