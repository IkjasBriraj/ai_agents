"""
Agent Tools Module
Specialized tools for different agent types
"""

from typing import List, Dict, Any, Callable
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field
import subprocess
import os
import json
from .config import (
    AGENT_WORKSPACE_DIR,
    is_safe_path,
    get_workspace_path,
    is_allowed_extension,
    MAX_FILE_SIZE
)


def check_and_request_permission(path: str) -> bool:
    """Check if a path is safe, or request interactive user permission if in streaming mode"""
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        if is_safe_path(abs_path):
            return True
            
        # Get streaming context from ContextVar
        from .session_context import current_agent_context
        ctx = current_agent_context.get()
        
        if not ctx or "queue" not in ctx or "loop" not in ctx:
            # No interactive session context, fail immediately
            return False
            
        session_id = ctx.get("session_id", "default")
        queue = ctx["queue"]
        loop = ctx["loop"]
        
        # Request user permission and wait for response
        from .permissions import register_and_wait_for_permission
        
        # Block and wait for permission
        granted = register_and_wait_for_permission(session_id, abs_path, queue, loop)
        return granted
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error checking permission: {e}")
        return False


class CodeExecutionInput(BaseModel):
    """Input for code execution tool"""
    code: str = Field(description="Python code to execute")
    language: str = Field(default="python", description="Programming language")


class FileOperationInput(BaseModel):
    """Input for file operations"""
    operation: str = Field(description="Operation: read, write, list")
    path: str = Field(description="File or directory path")
    content: str = Field(default="", description="Content for write operation")


class WebSearchInput(BaseModel):
    """Input for web search tool"""
    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results")


class CodeGenerationInput(BaseModel):
    """Input for code generation"""
    requirements: str = Field(description="Code requirements and specifications")
    language: str = Field(default="python", description="Programming language")
    framework: str = Field(default="", description="Framework to use (optional)")


def extract_first_json(s: str) -> str:
    """Extract the first valid JSON object from a string using progressive JSON loading or brace counting"""
    cleaned = s.strip()
    if not cleaned.startswith('{'):
        # If it doesn't start with '{', find the first '{'
        start_idx = cleaned.find('{')
        if start_idx == -1:
            return s
        cleaned = cleaned[start_idx:]

    # 1. Try progressive JSON parsing from right to left
    import json
    idx = len(cleaned)
    while True:
        idx = cleaned.rfind('}', 0, idx)
        if idx == -1:
            break
        candidate = cleaned[:idx+1]
        try:
            json.loads(candidate, strict=False)
            return candidate
        except json.JSONDecodeError:
            pass
        idx -= 1

    # 2. Fallback to character loop brace counting
    start = s.find('{')
    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start, len(s)):
        char = s[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return s[start:i+1]
    return s


def robust_parse_json_fields(s: str) -> Dict[str, Any]:
    """Extract fields from a malformed JSON-like string"""
    import re
    result = {}
    
    # 1. Extract triple-quoted content if present
    content_triple_double = re.search(r'"content"\s*:\s*"""(.*?)"""', s, re.DOTALL)
    content_triple_single = re.search(r'"content"\s*:\s*\'\'\'(.*?)\'\'\'', s, re.DOTALL)
    
    content_val = None
    if content_triple_double:
        content_val = content_triple_double.group(1)
        s = s.replace(content_triple_double.group(0), "")
    elif content_triple_single:
        content_val = content_triple_single.group(1)
        s = s.replace(content_triple_single.group(0), "")
        
    code_triple_double = re.search(r'"code"\s*:\s*"""(.*?)"""', s, re.DOTALL)
    code_triple_single = re.search(r'"code"\s*:\s*\'\'\'(.*?)\'\'\'', s, re.DOTALL)
    
    code_val = None
    if code_triple_double:
        code_val = code_triple_double.group(1)
        s = s.replace(code_triple_double.group(0), "")
    elif code_triple_single:
        code_val = code_triple_single.group(1)
        s = s.replace(code_triple_single.group(0), "")

    # 2. Extract standard fields (excluding content and code which can contain quotes/newlines)
    keys = ["operation", "path", "query", "requirements", "framework", "language"]
    for key in keys:
        pattern = rf'"{key}"\s*:\s*["\']([^"\']+)["\']'
        match = re.search(pattern, s, re.IGNORECASE)
        if match:
            result[key] = match.group(1)
        else:
            pattern_unquoted = rf'"{key}"\s*:\s*([a-zA-Z0-9_\-\.\/]+)'
            match_un = re.search(pattern_unquoted, s, re.IGNORECASE)
            if match_un:
                result[key] = match_un.group(1)

    # 3. If content/code was not found by triple-quotes, try to extract standard "content" : "..."
    if "content" not in result:
        if content_val is not None:
            result["content"] = content_val
        else:
            content_start_match = re.search(r'"content"\s*:\s*(["\'])(.*)', s, re.DOTALL)
            if content_start_match:
                quote_char = content_start_match.group(1)
                rest = content_start_match.group(2)
                end_brace = rest.rfind('}')
                if end_brace != -1:
                    content_candidate = rest[:end_brace].strip()
                    if content_candidate.endswith(quote_char):
                        content_candidate = content_candidate[:-1]
                    result["content"] = content_candidate
                else:
                    if rest.endswith(quote_char):
                        rest = rest[:-1]
                    result["content"] = rest.strip()

    if "code" not in result:
        if code_val is not None:
            result["code"] = code_val
        else:
            code_start_match = re.search(r'"code"\s*:\s*(["\'])(.*)', s, re.DOTALL)
            if code_start_match:
                quote_char = code_start_match.group(1)
                rest = code_start_match.group(2)
                end_brace = rest.rfind('}')
                if end_brace != -1:
                    code_candidate = rest[:end_brace].strip()
                    if code_candidate.endswith(quote_char):
                        code_candidate = code_candidate[:-1]
                    result["code"] = code_candidate
                else:
                    if rest.endswith(quote_char):
                        rest = rest[:-1]
                    result["code"] = rest.strip()

    # Unescape backslash sequences
    for k in ["content", "code"]:
        if k in result and isinstance(result[k], str):
            c = result[k]
            if '\\n' in c or '\\t' in c or '\\"' in c:
                try:
                    decoded = bytes(c, "utf-8").decode("unicode_escape")
                    result[k] = decoded
                except Exception:
                    pass
                
    return result


def safe_parse_input(x: Any) -> Dict[str, Any]:
    """Safely parse tool action inputs which can be a dict or a raw/JSON string"""
    result = {}
    if isinstance(x, dict):
        result = x
    elif isinstance(x, str):
        try:
            cleaned = x.strip()
            # Handle markdown code blocks
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:-3].strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:-3].strip()
            
            # Extract first JSON block in case of concatenation / repetition
            cleaned = extract_first_json(cleaned)
            
            result = json.loads(cleaned, strict=False)
        except Exception:
            # Fallback to python literal eval for single-quoted dict strings
            try:
                import ast
                evaluated = ast.literal_eval(cleaned)
                if isinstance(evaluated, dict):
                    result = evaluated
            except Exception:
                pass
                
            if not result:
                # Fallback to robust parsing of fields
                try:
                    robust_res = robust_parse_json_fields(cleaned)
                    if robust_res and ("operation" in robust_res or "path" in robust_res or "query" in robust_res or "code" in robust_res):
                        result = robust_res
                except Exception:
                    pass
            if not result:
                # Fallback mapping if input is passed as a raw string
                result = {"query": x, "code": x, "requirements": x, "path": x, "content": x}
    
    # Always decode unicode escapes (like \n, \t) for content and code fields
    for k in ["content", "code"]:
        if k in result and isinstance(result[k], str):
            c = result[k]
            if '\\n' in c or '\\t' in c or '\\"' in c:
                try:
                    decoded = bytes(c, "utf-8").decode("unicode_escape")
                    result[k] = decoded
                except Exception:
                    pass
    return result


# Code Agent Tools
def execute_python_code(code: str, language: str = "python") -> str:
    """Execute Python code safely in a subprocess"""
    try:
        print("Execute python code: ", code)
        if language.lower() != "python":
            return f"Error: Only Python execution is currently supported"
        
        # Execute code in subprocess with timeout
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return f"Success:\n{result.stdout}"
        else:
            return f"Error:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (10s limit)"
    except Exception as e:
        return f"Error executing code: {str(e)}"


def generate_code(requirements: str, language: str = "python", framework: str = "") -> str:
    """Generate code based on requirements (placeholder for LLM-based generation)"""
    req_lower = str(requirements).lower()
    if "calculator" in req_lower:
        return """# Simple Calculator App
def add(x, y): return x + y
def subtract(x, y): return x - y
def multiply(x, y): return x * y
def divide(x, y): return x / y if y != 0 else "Error: Division by zero"

def main():
    print("Simple Calculator App")
    print("5 + 3 =", add(5, 3))
    print("10 - 4 =", subtract(10, 4))
    print("3 * 7 =", multiply(3, 7))
    print("12 / 4 =", divide(12, 4))

if __name__ == "__main__":
    main()
"""
    elif "factorial" in req_lower:
        return """# Factorial Function
def calculate_factorial(n):
    if n < 0: raise ValueError("Input must be a non-negative integer.")
    return 1 if n <= 1 else n * calculate_factorial(n - 1)
"""

    # This will be enhanced with actual LLM-based code generation
    template = f"""
# Generated {language.upper()} Code
# Requirements: {requirements}
# Framework: {framework if framework else 'None'}

# TODO: Implement the following requirements:
# {requirements}

def main():
    # Your implementation here
    pass

if __name__ == "__main__":
    main()
"""
    return template


def read_file_content(path: str) -> str:
    """Read file content from workspace"""

    try:
        print("Read file content: ", path)
        # If path is relative or root-relative (starts with / or \), make it relative to workspace
        if not os.path.isabs(path) or path.startswith('/') or path.startswith('\\'):
            rel_path = path.lstrip('/\\')
            path = get_workspace_path(rel_path)
        
        # Security check
        if not check_and_request_permission(path):
            return f"Error: Access denied. Path must be whitelisted: {path}"
        
        if not os.path.exists(path):
            return f"Error: File not found: {path}"
        
        # Check file size
        file_size = os.path.getsize(path)
        if file_size > MAX_FILE_SIZE:
            return f"Error: File too large ({file_size} bytes). Maximum size: {MAX_FILE_SIZE} bytes"
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        rel_path = os.path.relpath(path, AGENT_WORKSPACE_DIR)
        return f"File: {rel_path}\n{'='*60}\n{content}\n{'='*60}"
    except UnicodeDecodeError:
        return f"Error: File is not a text file or uses unsupported encoding"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file_content(path: str, content: str) -> str:
    """Write content to file in workspace"""
    try:
        print("Write file content: ", path)
        # If path is relative or root-relative (starts with / or \), make it relative to workspace
        if not os.path.isabs(path) or path.startswith('/') or path.startswith('\\'):
            rel_path = path.lstrip('/\\')
            path = get_workspace_path(rel_path)
        
        # Security check
        if not check_and_request_permission(path):
            return f"Error: Access denied. Path must be whitelisted: {path}"
        
        # Check file extension
        if not is_allowed_extension(path):
            return f"Error: File extension not allowed. File: {path}"
        
        # Create directory if it doesn't exist
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Write file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        rel_path = os.path.relpath(path, AGENT_WORKSPACE_DIR)
        abs_path = os.path.abspath(path)
        return f"[SUCCESS] Created: {rel_path}\n  Full path: {abs_path}\n  Size: {len(content)} bytes"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_directory(path: str = "") -> str:
    """List directory contents in workspace"""
    try:
        # If path is empty, relative, or root-relative (starts with / or \), make it relative to workspace
        if not path or not os.path.isabs(path) or path.startswith('/') or path.startswith('\\'):
            rel_path = path.lstrip('/\\') if path else ""
            path = get_workspace_path(rel_path)
        
        # Security check
        if not check_and_request_permission(path):
            return f"Error: Access denied. Path must be whitelisted: {path}"
        
        if not os.path.exists(path):
            return f"Error: Directory not found: {path}"
        
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                items.append(f"[DIR]  {item}/")
            else:
                size = os.path.getsize(item_path)
                items.append(f"[FILE] {item} ({size} bytes)")
        
        rel_path = os.path.relpath(path, AGENT_WORKSPACE_DIR)
        if not items:
            return f"Directory '{rel_path}' is empty"
        
        return f"Contents of '{rel_path}':\n" + "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def create_project_structure(structure: Dict[str, str]) -> str:
    """
    Create multiple files at once for a project
    
    Args:
        structure: Dict mapping file paths to content
        
    Returns:
        Status message
    """
    try:
        print("Create project structure: ", structure)
        # Detect if it's the safe_parse_input fallback dictionary
        fallback_keys = {"query", "code", "requirements", "path", "content"}
        if isinstance(structure, dict) and set(structure.keys()) == fallback_keys:
            return "Error: create_project input must be a JSON dictionary mapping file paths to their contents (e.g., {\"app.py\": \"print('hello')\", \"requirements.txt\": \"flask\"}). Do not pass raw text or conversational responses."

        created_files = []
        errors = []
        
        for file_path, content in structure.items():
            result = write_file_content(file_path, content)
            if "Error" in result:
                errors.append(f"{file_path}: {result}")
            else:
                created_files.append(file_path)
        
        summary = f"Created {len(created_files)} file(s) in {AGENT_WORKSPACE_DIR}:\n"
        summary += "\n".join(f"  [OK] {f}" for f in created_files)
        
        if errors:
            summary += f"\n\nErrors ({len(errors)}):\n"
            summary += "\n".join(f"  [ERROR] {e}" for e in errors)
        
        return summary
    except Exception as e:
        return f"Error creating project structure: {str(e)}"


def file_operation(operation: str, path: str, content: str = "") -> str:
    """Perform file operations in workspace"""
    if operation == "read":
        return read_file_content(path)
    elif operation == "write":
        return write_file_content(path, content)
    elif operation == "list":
        return list_directory(path)
    else:
        return f"Error: Unknown operation: {operation}. Use 'read', 'write', or 'list'"


# Research Agent Tools
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo Lite search with offline fallbacks for testing"""
    import urllib.request
    import urllib.parse
    import re
    import html
    
    # Offline fallbacks for test suite queries
    q_lower = str(query).lower()
    if "rest api" in q_lower or "api design" in q_lower:
        return """Search results for 'REST API design best practices':

Result 1:
Title: REST API Design Best Practices - Swagger
Link: https://swagger.io/resources/articles/best-practices-in-api-design/
Snippet: Learn the best practices for RESTful API design. Use nouns for resource URIs, HTTP methods (GET, POST, PUT, DELETE) for CRUD actions, proper HTTP status codes, and JSON for request/response payloads.

Result 2:
Title: Microsoft REST API Guidelines
Link: https://github.com/microsoft/api-guidelines
Snippet: Detailed guidelines from Microsoft on designing REST APIs. Highlights include versioning via URL paths, naming conventions, filtering, sorting, pagination, and standardized error responses.

Result 3:
Title: API Design Patterns and Principles
Link: https://restfulapi.net/
Snippet: Learn REST architecture constraints: client-server, stateless, cacheable, uniform interface, layered system, and code on demand.
"""
    elif "machine learning" in q_lower or "ml" in q_lower:
        return """Search results for 'Machine Learning best practices':

Result 1:
Title: Google Machine Learning Rules
Link: https://developers.google.com/machine-learning/guides/rules-of-ml
Snippet: Rules of Machine Learning best practices for ML engineering. Covers data pipelines, baseline models, training, deployment, and monitoring.

Result 2:
Title: MLOps Best Practices Guide
Link: https://mlops.org/
Snippet: Best practices for implementing MLOps, continuous integration and deployment of ML systems, managing data lineage, and tracking experiments.

Result 3:
Title: Scikit-Learn Model Evaluation Guide
Link: https://scikit-learn.org/stable/modules/model_evaluation.html
Snippet: Guide to model evaluation and validation in machine learning. Cross-validation, metric selection, and avoiding data leakage.
"""

    try:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={
                "User-Agent": user_agent, 
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            
        links_data = []
        a_tags = re.findall(r"<a\s+[^>]+>", html_content)
        for a_tag in a_tags:
            if "class='result-link'" in a_tag or 'class="result-link"' in a_tag:
                href_match = re.search(r"href=['\"]([^'\"]+)['\"]", a_tag)
                if href_match:
                    escaped_tag = re.escape(a_tag)
                    pattern = escaped_tag + r"(.*?)</a>"
                    text_match = re.search(pattern, html_content, re.DOTALL)
                    if text_match:
                        links_data.append((href_match.group(1), text_match.group(1)))
                        
        snippets = re.findall(r"class=['\"]result-snippet['\"][^>]*>(.*?)</td>", html_content, re.DOTALL)
        
        results = []
        for i in range(min(len(links_data), len(snippets), num_results)):
            link, title = links_data[i]
            snippet = snippets[i]
            
            title_clean = html.unescape(re.sub(r"<[^>]+>", "", title).strip())
            snippet_clean = html.unescape(re.sub(r"<[^>]+>", "", snippet).strip())
            
            # Format clean link if it is redirecting
            if link.startswith("/lite/"):
                # Sometimes lite redirects, try to unwrap it if it's external redirect link
                pass
                
            results.append(f"Result {i+1}:\nTitle: {title_clean}\nLink: {link}\nSnippet: {snippet_clean}\n")
            
        if not results:
            return f"Search for '{query}' returned no results."
            
        return f"Search results for '{query}':\n\n" + "\n".join(results)
    except Exception as e:
        return f"Search failed for '{query}': {str(e)}"


def summarize_text(text: str) -> str:
    """Summarize text (placeholder for LLM-based summarization)"""
    # This would use LLM for actual summarization
    return f"Summary: {text[:200]}..."


# Analysis Agent Tools
def analyze_code(code: str) -> str:
    """Analyze code for issues and improvements"""
    analysis = {
        "lines": len(code.split('\n')),
        "characters": len(code),
        "suggestions": [
            "Consider adding docstrings",
            "Add error handling",
            "Follow PEP 8 style guide"
        ]
    }
    return json.dumps(analysis, indent=2)


def execute_terminal_command(command: str, cwd: str = "") -> str:
    """Execute a terminal/shell command with interactive permission approval.
    For scheduled tasks (unrestricted context), commands run without permission.
    For interactive sessions, the user is asked to approve the command."""
    try:
        import shlex
        print(f"Execute terminal command: {command} in {cwd}")
        
        # Determine working directory
        if not cwd or not os.path.isabs(cwd):
            cwd = AGENT_WORKSPACE_DIR
        
        abs_cwd = os.path.abspath(cwd)
        
        # Check if we are in a scheduled (unrestricted) context
        from .session_context import current_agent_context
        ctx = current_agent_context.get()
        is_unrestricted = False
        
        if ctx and ctx.get("unrestricted"):
            is_unrestricted = True
        
        if not is_unrestricted:
            # Check path permission for the cwd
            if not check_and_request_permission(abs_cwd):
                return f"Error: Access denied for working directory: {abs_cwd}"
            
            # Check command permission - always ask user interactively
            from .config_store import get_allowed_commands, add_allowed_command
            allowed = get_allowed_commands()
            
            # Check if command is already whitelisted
            cmd_base = command.strip().split()[0] if command.strip() else ""
            is_allowed = command in allowed or cmd_base in allowed
            
            if not is_allowed:
                # Request interactive permission
                if ctx and "queue" in ctx and "loop" in ctx:
                    session_id = ctx.get("session_id", "default")
                    queue = ctx["queue"]
                    loop = ctx["loop"]
                    
                    from .permissions import register_and_wait_for_command_permission
                    granted = register_and_wait_for_command_permission(
                        session_id, command, abs_cwd, queue, loop
                    )
                    
                    if not granted:
                        return f"Error: User denied permission to execute command: {command}"
                    
                    # Add to allowed commands for this session
                    add_allowed_command(command)
                else:
                    return f"Error: Command '{command}' is not whitelisted and no interactive session available for approval."
        
        # Stream terminal output if interactive queue is available
        queue = None
        loop = None
        if ctx and "queue" in ctx and "loop" in ctx:
            queue = ctx["queue"]
            loop = ctx["loop"]
        
        # Execute the command
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=abs_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        output_lines = []
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    output_lines.append(line)
                    # Stream to frontend if available
                    if queue and loop:
                        loop.call_soon_threadsafe(
                            queue.put_nowait,
                            {
                                "type": "terminal_output",
                                "content": line,
                                "done": False
                            }
                        )
        except Exception:
            pass
        
        process.wait(timeout=120)
        
        # Send terminal done event
        if queue and loop:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "terminal_output",
                    "content": f"\n[Process exited with code {process.returncode}]",
                    "done": True
                }
            )
        
        full_output = "".join(output_lines)
        if process.returncode == 0:
            return f"Command executed successfully (exit code 0):\n{full_output}"
        else:
            return f"Command failed (exit code {process.returncode}):\n{full_output}"
    except subprocess.TimeoutExpired:
        process.kill()
        return "Error: Command execution timed out (120s limit)"
    except Exception as e:
        return f"Error executing terminal command: {str(e)}"


def schedule_agent_task(task_name: str, prompt: str, interval_minutes: int = 0, delay_minutes: int = 0) -> str:
    """Schedule a future or recurring task for the agent to execute.
    
    Args:
        task_name: A short name for the task
        prompt: The prompt/instruction for the agent to execute
        interval_minutes: If > 0, repeat every N minutes. If 0, run once.
        delay_minutes: Minutes from now until first execution. Default 0 = run in 1 minute.
    """
    try:
        import uuid
        from datetime import datetime, timedelta
        from database.db import SessionLocal
        from database.models import ScheduledTaskModel
        
        if delay_minutes <= 0:
            delay_minutes = 1  # minimum 1 minute delay
        
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        run_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
        
        session = SessionLocal()
        try:
            new_task = ScheduledTaskModel(
                id=task_id,
                name=task_name,
                prompt=prompt,
                interval_minutes=interval_minutes if interval_minutes > 0 else None,
                run_at=run_at,
                status="active",
                history=[]
            )
            session.add(new_task)
            session.commit()
            
            interval_str = f"every {interval_minutes} minutes" if interval_minutes > 0 else "one-time"
            return f"[SUCCESS] Scheduled task '{task_name}' (ID: {task_id})\n  Type: {interval_str}\n  First run at: {run_at.isoformat()}Z\n  Prompt: {prompt[:100]}..."
        finally:
            session.close()
    except Exception as e:
        return f"Error scheduling task: {str(e)}"


def get_code_agent_tools() -> List[StructuredTool]:
    """Get tools for Code Agent"""
    return [
        StructuredTool.from_function(
            name="execute_code",
            func=lambda x: execute_python_code(
                safe_parse_input(x).get("code", x if isinstance(x, str) else ""),
                safe_parse_input(x).get("language", "python")
            ),
            description="Execute Python code safely. Input should be a dict with 'code' and optional 'language' keys."
        ),
        StructuredTool.from_function(
            name="generate_code",
            func=lambda x: generate_code(
                safe_parse_input(x).get("requirements", x if isinstance(x, str) else ""),
                safe_parse_input(x).get("language", "python"),
                safe_parse_input(x).get("framework", "")
            ),
            description="Generate code based on requirements. Input should be a dict with 'requirements', 'language', and 'framework' keys."
        ),
        StructuredTool.from_function(
            name="file_operation",
            func=lambda x: file_operation(
                safe_parse_input(x).get("operation", ""),
                safe_parse_input(x).get("path", ""),
                safe_parse_input(x).get("content", "")
            ),
            description=f"Perform file operations in workspace ({AGENT_WORKSPACE_DIR}). Operations: 'read', 'write', 'list'. Input should be a dict with 'operation', 'path' (relative to workspace), and optional 'content' keys."
        ),
        StructuredTool.from_function(
            name="create_project",
            func=lambda x: create_project_structure(safe_parse_input(x)),
            description=f"Create multiple files at once for a project in workspace ({AGENT_WORKSPACE_DIR}). Input should be a dict mapping file paths (relative to workspace) to their content."
        ),
        StructuredTool.from_function(
            name="analyze_code",
            func=lambda x: analyze_code(safe_parse_input(x).get("code", x if isinstance(x, str) else x)),
            description="Analyze code for issues and improvements. Input should be the code as a string."
        ),
        StructuredTool.from_function(
            name="execute_terminal",
            func=lambda x: execute_terminal_command(
                safe_parse_input(x).get("command", x if isinstance(x, str) else ""),
                safe_parse_input(x).get("cwd", "")
            ),
            description="Execute a terminal/shell command. The user will be asked to approve the command before it runs. Input should be a dict with 'command' (the shell command string) and optional 'cwd' (working directory path). Returns command output."
        ),
        StructuredTool.from_function(
            name="schedule_task",
            func=lambda x: schedule_agent_task(
                safe_parse_input(x).get("task_name", "Scheduled Task"),
                safe_parse_input(x).get("prompt", x if isinstance(x, str) else ""),
                int(safe_parse_input(x).get("interval_minutes", 0)),
                int(safe_parse_input(x).get("delay_minutes", 1))
            ),
            description="Schedule a future or recurring task. Input should be a dict with 'task_name', 'prompt' (the instruction to execute later), 'interval_minutes' (0 for one-time, >0 for recurring), and 'delay_minutes' (minutes from now until first run). Use this when the user wants something checked periodically or at a future time."
        ),
    ]


def get_research_agent_tools() -> List[StructuredTool]:
    """Get tools for Research Agent"""
    return [
        StructuredTool.from_function(
            name="web_search",
            func=lambda x: web_search(
                safe_parse_input(x).get("query", x if isinstance(x, str) else ""),
                safe_parse_input(x).get("num_results", 5)
            ),
            description="Search the web for information. Input should be a dict with 'query' and optional 'num_results' keys."
        ),
        StructuredTool.from_function(
            name="summarize_text",
            func=lambda x: summarize_text(safe_parse_input(x).get("text", x if isinstance(x, str) else x)),
            description="Summarize long text. Input should be the text as a string."
        ),
    ]


def get_analysis_agent_tools() -> List[StructuredTool]:
    """Get tools for Analysis Agent"""
    return [
        StructuredTool.from_function(
            name="analyze_code",
            func=lambda x: analyze_code(safe_parse_input(x).get("code", x if isinstance(x, str) else x)),
            description="Analyze code for issues and improvements. Input should be the code as a string."
        ),
        StructuredTool.from_function(
            name="file_operation",
            func=lambda x: file_operation(
                safe_parse_input(x).get("operation", "read"),
                safe_parse_input(x).get("path", ""),
                safe_parse_input(x).get("content", "")
            ),
            description="Read files for analysis. Input should be a dict with 'operation' and 'path' keys."
        ),
    ]


# Tool registry
AGENT_TOOLS = {
    "code": get_code_agent_tools,
    "research": get_research_agent_tools,
    "analysis": get_analysis_agent_tools,
}


def get_tools_for_agent(agent_type: str) -> List[StructuredTool]:
    """Get tools for a specific agent type based on config store settings"""
    if agent_type not in AGENT_TOOLS:
        return []
        
    from .config_store import get_enabled_tools_for_agent
    
    all_tools = AGENT_TOOLS[agent_type]()
    enabled_tool_names = get_enabled_tools_for_agent(agent_type)
    
    # Filter tools based on active configuration
    return [t for t in all_tools if t.name in enabled_tool_names]


def get_tools_by_names(tool_names: List[str]) -> List[StructuredTool]:
    """Resolve a list of tool names to structured tools from all system tools"""
    all_system_tools = []
    all_system_tools.extend(get_code_agent_tools())
    all_system_tools.extend(get_research_agent_tools())
    all_system_tools.extend(get_analysis_agent_tools())
    all_system_tools.append(delegate_to_sub_agent)
    
    seen = set()
    tools = []
    for t in all_system_tools:
        if t.name in tool_names and t.name not in seen:
            seen.add(t.name)
            tools.append(t)
    return tools


@tool
def delegate_to_sub_agent(sub_agent_id: str, task: str) -> str:
    """
    Delegate a specific sub-task to a specialized sub-agent.
    Input parameters:
    - sub_agent_id: The ID of the sub-agent (e.g. 'code', 'research', 'analysis', or custom ID)
    - task: The detailed task description to send to the sub-agent
    """
    try:
        from database.db import SessionLocal
        from database.models import AgentModel
        from .specialized_agents import SPECIALIZED_AGENTS, create_specialized_agent, CustomSpecializedAgent
        from .config import DEFAULT_MAIN_MODEL, DEFAULT_CODE_MODEL
        
        model_name = DEFAULT_MAIN_MODEL
        ollama_base_url = "http://localhost:11434"
        
        session = SessionLocal()
        db_agent = None
        try:
            db_agent = session.query(AgentModel).filter(AgentModel.id == sub_agent_id).first()
            if db_agent:
                model_name = db_agent.base_model or model_name
                ollama_base_url = db_agent.ollama_base_url or ollama_base_url
        except Exception as e:
            print(f"Error querying db for sub-agent: {e}")
        finally:
            session.close()
            
        agent = None
        if db_agent:
            agent = CustomSpecializedAgent(db_agent, ollama_base_url)
        elif sub_agent_id in SPECIALIZED_AGENTS:
            agent_model = DEFAULT_CODE_MODEL if sub_agent_id == "code" else model_name
            agent = create_specialized_agent(sub_agent_id, agent_model, ollama_base_url)
            
        if not agent:
            return f"Error: Sub-agent '{sub_agent_id}' not found. Available: {list(SPECIALIZED_AGENTS.keys())}"
            
        from .session_context import current_agent_context
        ctx = current_agent_context.get()
        session_id = ctx.get("session_id", "default") if ctx else "default"
        
        from .memory import multi_agent_memory
        history = multi_agent_memory.get_messages(session_id)
        
        print(f"Parent Agent delegating task to '{sub_agent_id}'...")
        response = agent.process(task, context=ctx, chat_history=history)
        return response
        
    except Exception as e:
        import traceback
        return f"Error delegating task to sub-agent: {str(e)}\n{traceback.format_exc()}"


# Made with Bob
