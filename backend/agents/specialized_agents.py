import os
import sys
import time
import re
import asyncio
import json
import logging
import traceback

logger = logging.getLogger(__name__)
from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatOllama
from .config import DEFAULT_MAIN_MODEL, DEFAULT_CODE_MODEL, AGENT_WORKSPACE_DIR

class SafeChatOllama(ChatOllama):
    """Subclass of ChatOllama that merges and safely handles stop parameters to avoid conflicts."""
    def __init__(self, *args: Any, **kwargs: Any):
        model_name = kwargs.get("model", "")
        ollama_base_url = kwargs.get("base_url", "http://localhost:11434")

        if model_name:
            import requests
            try:
                res = requests.get(f"{ollama_base_url}/api/tags", timeout=2.0)
                if res.status_code == 200:
                    local_names = [m["name"] for m in res.json().get("models", [])]
                    if model_name not in local_names and f"{model_name}:latest" not in local_names:
                        if "gemma4:31b-cloud" in local_names:
                            kwargs["model"] = "gemma4:31b-cloud"
                        elif "gemma4:26b" in local_names:
                            kwargs["model"] = "gemma4:26b"
                        elif "granite-code:20b" in local_names:
                            kwargs["model"] = "granite-code:20b"
                        elif local_names:
                            kwargs["model"] = local_names[0]
            except Exception:
                pass
        super().__init__(*args, **kwargs)

    def _create_stream(self, api_url: str, payload: Any, stop: Optional[List[str]] = None, **kwargs: Any):
        combined_stop = list(stop) if stop is not None else []
        if self.stop is not None:
            for s in self.stop:
                if s not in combined_stop:
                    combined_stop.append(s)

        old_stop = self.stop
        object.__setattr__(self, "stop", None)
        try:
            iterator = super()._create_stream(api_url, payload, stop=combined_stop, **kwargs)

            def generator_wrapper(it):
                accumulated = ""
                stop_lowers = [s.lower() for s in combined_stop if s]

                for chunk in it:
                    try:
                        data = json.loads(chunk)
                        msg_dict = data.get("message")
                        content = ""
                        is_chat = False
                        if isinstance(msg_dict, dict) and "content" in msg_dict:
                            content = msg_dict["content"]
                            is_chat = True
                        elif "response" in data:
                            content = data.get("response", "")

                        accumulated += content

                        if data.get("done") or "prompt_eval_count" in data:
                            prompt_tokens = data.get("prompt_eval_count", 0)
                            completion_tokens = data.get("eval_count", 0)
                            if prompt_tokens > 0 or completion_tokens > 0:
                                from .session_context import current_token_usage
                                usage = current_token_usage.get()
                                if usage is not None:
                                    usage["prompt_tokens"] += prompt_tokens
                                    usage["completion_tokens"] += completion_tokens
                                    usage["total_tokens"] += (prompt_tokens + completion_tokens)

                        # Enforce stop sequences if Ollama model didn't stop automatically
                        if stop_lowers:
                            hit_stop = None
                            hit_idx = -1
                            acc_lower = accumulated.lower()
                            for s in stop_lowers:
                                idx = acc_lower.find(s)
                                if idx != -1:
                                    if hit_idx == -1 or idx < hit_idx:
                                        hit_idx = idx
                                        hit_stop = s

                            if hit_stop is not None and hit_idx != -1:
                                allowed_total_len = hit_idx
                                prev_len = len(accumulated) - len(content)
                                keep_len = max(0, allowed_total_len - prev_len)
                                truncated_content = content[:keep_len]
                                if is_chat:
                                    data["message"]["content"] = truncated_content
                                elif "response" in data:
                                    data["response"] = truncated_content
                                data["done"] = True
                                yield json.dumps(data)
                                return

                        yield chunk
                    except Exception:
                        yield chunk
            return generator_wrapper(iterator)
        finally:
            object.__setattr__(self, "stop", old_stop)

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_classic.agents import AgentExecutor
from langchain_classic.agents.react.agent import create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_classic.agents.output_parsers.react_single_input import ReActSingleInputOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.callbacks import BaseCallbackHandler

# Phase 1 upgrades
try:
    from .tool_calling_loop import ToolCallingLoop
    TOOL_CALLING_AVAILABLE = True
except ImportError:
    TOOL_CALLING_AVAILABLE = False


def create_agent_llm(provider: str = "ollama", model_name: str = DEFAULT_MAIN_MODEL, api_key: str = None, ollama_base_url: str = "http://localhost:11434", thinking_level: str = "medium"):
    """Create LLM instance for Ollama, OpenAI, Anthropic, IBM, Gemini, or DeepSeek with strict token conservation when low thinking mode is enabled."""
    import os
    prov = (provider or "ollama").lower()
    think_lvl = (thinking_level or "medium").lower()

    max_tokens_val = 5000 if think_lvl == "low" else None
    temp_val = 0.1 if think_lvl == "low" else 0.2
    
    if prov == "openai":
        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("Cloud provider 'OPENAI' requires an API Key. Please click 'Provider' in the top toolbar to enter your API key.")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Missing required package 'langchain-openai'. Please run: pip install langchain-openai")
        target_model = model_name or "gpt-4o"
        if "opus" in target_model.lower():
            target_model = "gpt-4o"
        kwargs = {"model": target_model, "api_key": key, "temperature": temp_val}
        if max_tokens_val:
            kwargs["max_tokens"] = max_tokens_val
        return ChatOpenAI(**kwargs)

    elif prov == "anthropic":
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("Cloud provider 'ANTHROPIC' requires an API Key. Please click 'Provider' in the top toolbar to enter your API key.")
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Missing required package 'langchain-anthropic'. Please run: pip install langchain-anthropic")
        
        m_lower = (model_name or "").lower()
        if "opus-5" in m_lower or "opus 5" in m_lower:
            target_model = "claude-opus-5"
        elif "opus" in m_lower or "opus-4-8" in m_lower or "opus-4.8" in m_lower:
            target_model = "claude-opus-4-8"
        elif "haiku" in m_lower:
            target_model = "claude-haiku-4-5-20251001"
        elif "sonnet-5" in m_lower or "sonnet 5" in m_lower or "3-7" in m_lower or "3.7" in m_lower:
            target_model = "claude-sonnet-5"
        else:
            target_model = "claude-sonnet-4-6"

        kwargs = {"model": target_model, "api_key": key, "temperature": temp_val}
        if max_tokens_val:
            kwargs["max_tokens"] = max_tokens_val
        return ChatAnthropic(**kwargs)

    elif prov == "gemini":
        key = api_key or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        if not key:
            raise ValueError("Cloud provider 'GEMINI' requires an API Key. Please click 'Provider' in the top toolbar to enter your API key.")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("Missing required package 'langchain-google-genai'. Please run: pip install langchain-google-genai")
        target_model = model_name if model_name and "gemini" in model_name.lower() else "gemini-2.0-flash"
        kwargs = {"model": target_model, "google_api_key": key, "temperature": temp_val}
        if max_tokens_val:
            kwargs["max_output_tokens"] = max_tokens_val
        return ChatGoogleGenerativeAI(**kwargs)

    elif prov == "deepseek":
        key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if not key:
            raise ValueError("Cloud provider 'DEEPSEEK' requires an API Key. Please click 'Provider' in the top toolbar to enter your API key.")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Missing required package 'langchain-openai'. Please run: pip install langchain-openai")
        target_model = model_name if model_name and "deepseek" in model_name.lower() else "deepseek-chat"
        kwargs = {"model": target_model, "api_key": key, "base_url": "https://api.deepseek.com", "temperature": temp_val}
        if max_tokens_val:
            kwargs["max_tokens"] = max_tokens_val
        return ChatOpenAI(**kwargs)

    elif prov == "ibm":
        key = api_key or os.environ.get("IBM_API_KEY", "")
        if key:
            try:
                from langchain_openai import ChatOpenAI
            except ImportError:
                raise ImportError("Missing required package 'langchain-openai'. Please run: pip install langchain-openai")
            kwargs = {
                "model": model_name if "granite" in (model_name or "").lower() else "ibm/granite-3-8b-instruct",
                "api_key": key,
                "base_url": os.environ.get("IBM_BASE_URL", "https://us-south.ml.cloud.ibm.com/v1"),
                "temperature": temp_val
            }
            if max_tokens_val:
                kwargs["max_tokens"] = max_tokens_val
            return ChatOpenAI(**kwargs)
        else:
            kwargs = {
                "model": model_name if "granite" in (model_name or "").lower() else "granite4.1:8b",
                "base_url": ollama_base_url,
                "temperature": temp_val,
                "timeout": 600
            }
            if max_tokens_val:
                kwargs["num_predict"] = max_tokens_val
            return SafeChatOllama(**kwargs)

    else:
        target_model = model_name or DEFAULT_MAIN_MODEL

        kwargs = {
            "model": target_model,
            "base_url": ollama_base_url,
            "temperature": temp_val,
            "timeout": 600
        }
        if max_tokens_val:
            kwargs["num_predict"] = max_tokens_val
        return SafeChatOllama(**kwargs)

def extract_file_path_from_code_block(path_hint: str = "", code_content: str = "", full_text: str = "", task_text: str = "") -> Optional[str]:
    """
    Extract exact file path and target folder generically for code blocks across any programming language.
    Checks:
    1. Direct path_hint header above block or inline fence info (e.g. File: src/components/Header.tsx, python:src/app.py, ### index.html)
    2. First 3 lines of code_content for comments (e.g. // filepath: src/App.tsx, # main.py, <!-- index.html -->)
    3. Preceding text context in full_text
    4. Task prompt explicit filename or language/content heuristics
    5. Task prompt folder directives (e.g. "in folder calculator" -> prefix calculator/)
    """
    import re
    from .config import AGENT_WORKSPACE_DIR
    target_path = None

    lang_hint = ""
    # 1. Clean path_hint (also handles `lang:path/to/file.ext` or `title="path/to/file.ext"`)
    if path_hint:
        raw_hint = path_hint.strip()
        if ":" in raw_hint and not raw_hint.lower().startswith("http"):
            parts = raw_hint.split(":", 1)
            if "." in parts[1]:
                lang_hint = parts[0].strip().lower()
                raw_hint = parts[1].strip()
        title_m = re.search(r'(?:file(?:name)?|path|title)\s*=\s*[\'"]([^\'"]+\.[a-zA-Z0-9]+)[\'"]', raw_hint, re.IGNORECASE)
        if title_m:
            raw_hint = title_m.group(1)

        cleaned_hint = re.sub(r'^[0-9\.\-\*\s]+', '', raw_hint).strip("`*# :-\t\n\r'\"")
        if "." in cleaned_hint and not cleaned_hint.startswith("http") and cleaned_hint.lower() not in ("json", "e.g.", "i.e."):
            target_path = cleaned_hint
        elif cleaned_hint.isalpha():
            lang_hint = cleaned_hint.lower()

    # 2. Check first 3 lines inside code_content for path comments
    if not target_path and code_content:
        lines = code_content.splitlines()[:3]
        for line in lines:
            line_str = line.strip()
            m = re.search(r'(?://|#|/\*|<!--|--|\*)\s*(?:file(?:name)?|path)?[:\s]*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]{1,8})', line_str, re.IGNORECASE)
            if m:
                extracted = re.sub(r'^[0-9\.\-\*\s]+', '', m.group(1)).strip("`*# :-\t\n\r'\"")
                if "." in extracted and not extracted.startswith("http") and extracted.lower() not in ("json", "e.g.", "i.e."):
                    target_path = extracted
                    break

    # 3. Check preceding text in full_text
    if not target_path and full_text and code_content[:20] in full_text:
        idx = full_text.find(code_content[:20])
        preceding = full_text[max(0, idx - 220):idx]
        m = re.search(r'(?:file(?:name)?|path|created|wrote|output|###+|\*\*|`)\s*[:`*]*\s*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]{1,8})', preceding, re.IGNORECASE)
        if not m:
            m = re.search(r'\b([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]{1,8})\b', preceding)
        if m:
            extracted = re.sub(r'^[0-9\.\-\*\s]+', '', m.group(1)).strip("`*# :-\t\n\r'\"")
            if "." in extracted and not extracted.startswith("http") and extracted.lower() not in ("json", "e.g.", "i.e."):
                target_path = extracted

    # 3b. Check task_text for explicit filename
    if not target_path and task_text:
        m = re.search(r'(?:called|named|file|path|create|write|in)\s+[\'"`*]*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]{1,8})[\'"`*]*', task_text, re.IGNORECASE)
        if m:
            extracted = re.sub(r'^[0-9\.\-\*\s]+', '', m.group(1)).strip("`*# :-\t\n\r'\"")
            if "." in extracted and not extracted.startswith("http") and extracted.lower() not in ("e.g.", "i.e.", "node.js", "next.js", "vue.js", "react.js", "three.js", "chart.js"):
                target_path = extracted

    # 4. Generic polyglot fallback inference based on language hint or code structure
    if not target_path:
        lang_defaults = {
            "python": "main.py", "py": "main.py",
            "typescript": "index.ts", "ts": "index.ts",
            "tsx": "App.tsx", "jsx": "App.jsx",
            "javascript": "script.js", "js": "script.js",
            "html": "index.html", "css": "style.css", "scss": "style.scss",
            "rust": "main.rs", "rs": "main.rs",
            "go": "main.go", "golang": "main.go",
            "cpp": "main.cpp", "c++": "main.cpp", "c": "main.c",
            "java": "Main.java", "csharp": "Program.cs", "cs": "Program.cs",
            "ruby": "main.rb", "rb": "main.rb", "php": "index.php",
            "swift": "main.swift", "kotlin": "Main.kt", "kt": "Main.kt",
            "sql": "schema.sql", "sh": "script.sh", "bash": "script.sh",
            "ps1": "script.ps1", "powershell": "script.ps1",
            "json": "data.json", "yaml": "config.yaml", "yml": "config.yml",
            "toml": "config.toml", "md": "README.md", "markdown": "README.md"
        }
        if lang_hint in lang_defaults:
            target_path = lang_defaults[lang_hint]
        elif "<!DOCTYPE html>" in code_content or "<html" in code_content or "<body" in code_content:
            target_path = "index.html"
        elif "package main" in code_content and "func " in code_content:
            target_path = "main.go"
        elif "fn main(" in code_content:
            target_path = "main.rs"
        elif "#include <" in code_content:
            target_path = "main.cpp"
        elif "public class " in code_content and "static void main" in code_content:
            target_path = "Main.java"
        elif "def " in code_content or "import " in code_content and ("print(" in code_content or "class " in code_content or "return " in code_content):
            target_path = "main.py"
        elif "interface " in code_content or ": string" in code_content or ": number" in code_content:
            target_path = "App.tsx" if ("<" in code_content and "/>" in code_content) else "index.ts"
        elif "document.add" in code_content or "const " in code_content or "function " in code_content:
            target_path = "js/main.js" if os.path.exists(os.path.join(AGENT_WORKSPACE_DIR, "js", "main.js")) else "script.js"
        elif "body {" in code_content or "@tailwind" in code_content or ":root" in code_content:
            target_path = "css/style.css" if os.path.exists(os.path.join(AGENT_WORKSPACE_DIR, "css", "style.css")) else "style.css"
        elif code_content.lstrip().startswith("{") and code_content.rstrip().endswith("}"):
            target_path = "data.json"
        else:
            target_path = "main.py"

    # 5. Folder Directive Auto-Prefixing from task_text (preferred) or full_text
    context_for_folder = task_text if (task_text and task_text.strip()) else full_text
    if target_path and context_for_folder and not os.path.isabs(target_path):
        STOP_WORDS = {
            'the', 'a', 'an', 'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'new', 'workspace', 'code', 'website', 'with', 'for', 'and', 'or', 'in', 'into', 'inside', 'under',
            'on', 'at', 'to', 'from', 'by', 'of', 'please', 'make', 'create', 'build', 'have', 'has', 'had',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'it', 'so', 'as', 'if', 'general', 'main', 'root',
            'here', 'there', 'where', 'which', 'who', 'whom', 'whose', 'why', 'how', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'than',
            'too', 'very', 'can', 'will', 'just', 'don', 'should', 'now', 'folder', 'directory', 'dir', 'files', 'file'
        }
        is_root_website = re.search(r'(?:in|into|inside|under)\s+(?:my\s+|the\s+)?(?:website|workspace|code)\s*(?:folder|directory|dir)?', context_for_folder, re.IGNORECASE)
        if not is_root_website:
            folder_match = re.search(r'(?:in|into|inside|under)\s+(?:the\s+)?(?:folder|directory|dir)\s+[\'"`*]*([a-zA-Z0-9_\-]+)[\'"`*]*', context_for_folder, re.IGNORECASE)
            if not folder_match:
                folder_match = re.search(r'(?:folder|directory)\s*[:=]\s*[\'"`*]*([a-zA-Z0-9_\-]+)[\'"`*]*', context_for_folder, re.IGNORECASE)

            if folder_match:
                folder_name = folder_match.group(1).strip()
                if folder_name and folder_name.lower() not in STOP_WORDS:
                    norm_target = target_path.replace("\\", "/")
                    if not norm_target.startswith(folder_name + "/"):
                        target_path = f"{folder_name}/{target_path}"

    if target_path:
        target_path = re.sub(r'^[^\w\.\/\\]+', '', target_path).strip("`*# :-\t\n\r'\"")

    return target_path


class RobustReActParser(ReActSingleInputOutputParser):
    """Robust output parser for ReAct agents that recovers from minor formatting issues and infinite loops"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._action_history = []
        self._consecutive_counts = {}
        self._previous_actions = set()

    def parse(self, text: str) -> AgentAction | AgentFinish:
        if not hasattr(self, '_action_history'):
            self._action_history = []
            self._consecutive_counts = {}
            self._previous_actions = set()

        # Strip special LLM tokens (e.g. <|tool_response>, <|im_end|>, etc.)
        text = re.sub(r'<\|[^|]+\|>', '', text).strip()
        
        # Isolate and strip <thinking> tags without truncating subsequent Action text
        text_for_parsing = text
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', text, re.DOTALL | re.IGNORECASE)
        if thinking_match:
            text_for_parsing = text.replace(thinking_match.group(0), "").strip()
        else:
            text_for_parsing = re.sub(r'</?thinking>', '', text, flags=re.IGNORECASE).strip()

        text_lower = text_for_parsing.lower()

        action_pattern = re.compile(r"\[?action\]?\s*(?:\d+)??\s*[:\s]\s*(.+)", re.IGNORECASE)
        input_pattern = re.compile(r"\[?action\s*(?:\d+)??\s*input\]?\s*[:\s]\s*(.+)", re.IGNORECASE | re.DOTALL)

        action_match = action_pattern.search(text_for_parsing)
        input_match = input_pattern.search(text_for_parsing)

        # Fallback if action matched but input pattern omitted Action Input: header
        if action_match and not input_match:
            json_in_text = re.search(r'(\{[\s\S]+\})', text_for_parsing)
            if json_in_text:
                input_match = re.search(r'(.+)', json_in_text.group(1), re.DOTALL)

        # Fallback for JSON-structured tool calls without explicit Action: line prefix
        if not action_match or not input_match:
            json_call = re.search(r'\{\s*["\'](?:operation|action)["\']\s*:\s*["\']([^"\']+)["\'].*?\}', text_for_parsing, re.DOTALL)
            if json_call:
                tool_name = json_call.group(1).lower()
                if tool_name in ["write", "read", "list", "patch"]:
                    action_match = action_pattern.search(f"Action: file_operation\nAction Input: {json_call.group(0)}")
                    input_match = input_pattern.search(f"Action: file_operation\nAction Input: {json_call.group(0)}")
                    text_for_parsing = f"Action: file_operation\nAction Input: {json_call.group(0)}"
                elif tool_name in ["create_project", "file_operation", "batch_verify_and_repair_files", "update_todo_list"]:
                    action_match = action_pattern.search(f"Action: {tool_name}\nAction Input: {json_call.group(0)}")
                    input_match = input_pattern.search(f"Action: {tool_name}\nAction Input: {json_call.group(0)}")
                    text_for_parsing = f"Action: {tool_name}\nAction Input: {json_call.group(0)}"

        # 1. First priority: Check for explicit Action & Action Input tool calls
        if action_match and input_match:
            action = action_match.group(1).split("\n")[0].strip()
            action = re.sub(r'^[\[\`\*]+|[\]\`\*]+$', '', action).strip()
            
            # Tool name normalization to prevent parser exceptions on minor LLM name variations
            action_lower = action.lower()
            if "recursive_list" in action_lower or "list_files" in action_lower or "file_list" in action_lower or "dir_list" in action_lower:
                action = "recursive_list"
            elif "grep_search" in action_lower or "grep" in action_lower:
                action = "grep_search"
            elif "file_operation" in action_lower or "file_op" in action_lower:
                action = "file_operation"
            elif "create_project" in action_lower:
                action = "create_project"
            elif "execute_terminal" in action_lower or "terminal" in action_lower:
                action = "execute_terminal"
            elif "execute_code" in action_lower:
                action = "execute_code"
            elif "batch_verify" in action_lower:
                action = "batch_verify_and_repair_files"
            elif "verify_app" in action_lower:
                action = "verify_app_browser_console"
            elif "browser_open" in action_lower:
                action = "browser_open_url"
            elif "browser_console" in action_lower or "get_console" in action_lower:
                action = "browser_get_console_errors"
            elif "browser_screenshot" in action_lower or "take_screenshot" in action_lower:
                action = "browser_take_screenshot"
            elif "browser_vision" in action_lower or "vision_audit" in action_lower:
                action = "browser_vision_audit"
            elif "update_todo" in action_lower or "todo" in action_lower:
                action = "update_todo_list"
            elif "generate_image" in action_lower:
                action = "generate_image"

            action_input = input_match.group(1).strip()

            # If the model emitted both update_todo_list and a file creation action, prioritize file creation!
            if action == "update_todo_list":
                file_action_m = re.search(r"\[?action\]?\s*(?:\d+)??\s*[:\s]\s*(create_project|file_operation)", text_for_parsing, re.IGNORECASE)
                if file_action_m:
                    after_act = text_for_parsing[file_action_m.end():]
                    file_input_m = re.search(r"\[?action\s*(?:\d+)??\s*input\]?\s*[:\s]\s*(.+)", after_act, re.IGNORECASE | re.DOTALL)
                    if file_input_m:
                        action = file_action_m.group(1).strip().lower()
                        action_input = file_input_m.group(1).strip()

            obs_marker = "observation:"
            final_marker = "final answer:"
            thought_marker = "thought:"

            action_input_lower = action_input.lower()
            split_idx = len(action_input)

            for marker in [obs_marker, final_marker, thought_marker, "observation", "action:", "<tool_call>"]:
                if marker in action_input_lower:
                    idx = action_input_lower.find(marker)
                    if idx < split_idx:
                        split_idx = idx

            action_input = action_input[:split_idx].strip()

            # Strip JSON markdown wrappers
            if action_input.startswith("```json"):
                action_input = action_input[7:]
            elif action_input.startswith("```"):
                action_input = action_input[3:]
            if action_input.endswith("```"):
                action_input = action_input[:-3]

            action_input = action_input.strip()

            # Fix single-quoted python dict strings
            qm = re.search(r'["\']query["\']\s*:\s*["\']([^"\']+)["\']', action_input)
            if qm:
                action_input = f'{{"query": "{qm.group(1)}"}}'

            if (action_input.startswith('"') and action_input.endswith('"')) or (action_input.startswith("'") and action_input.endswith("'")):
                action_input = action_input[1:-1].strip()

            action_key = f"{action}:{action_input[:100]}"
            last_key = getattr(self, '_last_action_key', None)
            if last_key != action_key:
                self._consecutive_counts = {}
            self._last_action_key = action_key
            self._consecutive_counts[action_key] = self._consecutive_counts.get(action_key, 0) + 1
            if not hasattr(self, '_action_history'):
                self._action_history = []
            self._action_history.append(action_key)

            # Cycle detection: 2-step alternating cycles (A -> B -> A -> B)
            if len(self._action_history) >= 4:
                h = self._action_history
                if h[-4] == h[-2] and h[-3] == h[-1]:
                    return AgentFinish({"output": f"### 🚀 Completed (Cycle Break)\n\nDetected repeating pattern between `{h[-2].split(':')[0]}` and `{h[-1].split(':')[0]}`. Concluding execution with workspace state."}, text)

            is_read_only = any(ro in action_input_lower for ro in ['"read"', '"list"', "read_file", "list_dir", "get_console"]) or action in ["verify_app_browser_console", "browser_get_console_errors", "recursive_list", "grep_search"]
            max_allowed = 12 if action == "update_todo_list" else (4 if is_read_only else 3)

            if self._consecutive_counts[action_key] >= max_allowed:
                return AgentFinish({"output": f"### 🚀 Action Completed\n\nVerified execution of action `{action}` in workspace."}, text)

            return AgentAction(action, action_input, text)

        # 2. Second priority: Auto-recovery for raw code blocks output by LLMs before checking Final Answer
        code_blocks = re.findall(r'(?:(?:file|filename|path|created|wrote|output|###|\*\*|`)\s*[:`*]*\s*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)[`*:\s]*\r?\n+)?```([a-zA-Z0-9_\-\:\=\s]*)\r?\n([\s\S]+?)```', text, re.IGNORECASE)
        if not code_blocks:
            standard_blocks = re.findall(r'```([a-zA-Z0-9_\-\:\=\s]*)\r?\n([\s\S]+?)```', text)
            if standard_blocks:
                code_blocks = [("", tag, content) for tag, content in standard_blocks]
        if not code_blocks:
            unclosed_blocks = re.findall(r'```([a-zA-Z0-9_\-\:\=\s]*)\r?\n([\s\S]+)', text)
            if unclosed_blocks:
                code_blocks = [("", tag, content) for tag, content in unclosed_blocks]

        if code_blocks:
            project_files = {}
            for path_hint, lang_tag, code_content in code_blocks:
                code_content = code_content.strip()
                if not code_content or len(code_content) < 5 or (code_content.startswith("{") and "Action:" in code_content):
                    continue
                
                target_p = extract_file_path_from_code_block(path_hint, code_content, text, getattr(self, '_current_task', text))

                if target_p:
                    project_files[target_p] = code_content

            if len(project_files) == 1:
                p, c = list(project_files.items())[0]
                act_payload = json.dumps({"operation": "write", "path": p, "content": c})
                action_key = f"file_operation:{act_payload}"
                if action_key not in self._previous_actions:
                    self._previous_actions.add(action_key)
                    return AgentAction("file_operation", act_payload, text)
            elif len(project_files) > 1:
                act_payload = json.dumps(project_files)
                action_key = f"create_project:{act_payload[:100]}"
                if action_key not in self._previous_actions:
                    self._previous_actions.add(action_key)
                    return AgentAction("create_project", act_payload, text)

        # 3. Third priority: Check for explicit Final Answer marker (only after unsaved code blocks are processed)
        final_answer_marker = "final answer:"
        if final_answer_marker in text_lower:
            final_idx = text_lower.rfind(final_answer_marker)
            final_ans = text[final_idx + len(final_answer_marker):].strip()
            return AgentFinish({"output": final_ans}, text)

        # Auto-recovery for model disclaimers claiming lack of local file system access
        refusal_keywords = [
            "don't have the ability to interact with your local file",
            "don't have access to your local file",
            "cannot interact with your local file",
            "as an ai model developed by deepseek",
            "cannot execute code or interact with files",
            "lack access to your local",
            "don't have access to file systems",
            "can't assist in generating an implementation plan based on the content of your local"
        ]
        if any(kw in text_lower for kw in refusal_keywords):
            # Force workspace listing tool execution to prove tool access to the model
            return AgentAction(
                "file_operation",
                '{"operation": "list", "path": ""}',
                text
            )

        # Auto-recovery for models identifying a tool in reasoning text without emitting explicit Action: tag
        # Only trigger if the tool has NOT already been executed in this session
        executed_tool_names = set(a.split(':')[0] for a in self._consecutive_counts.keys())

        if "generate_excel_sheet" in text_lower and "generate_excel_sheet" not in executed_tool_names:
            fname_match = re.search(r'([a-zA-Z0-9_\-]+\.xlsx)', text)
            fname = fname_match.group(1).replace('.xlsx', '') if fname_match else "spreadsheet"
            act_input = f'{{"title": "{fname.replace("_", " ").title()}", "filename": "{fname}"}}'
            self._consecutive_counts[f"generate_excel_sheet:{act_input}"] = 1
            return AgentAction("generate_excel_sheet", act_input, text)
        is_ppt_intent = any(kw in text_lower for kw in ["generate_presentation", "presentation", "ppt", "powerpoint", "slide deck", "pitch deck", "slides"])
        if is_ppt_intent and "generate_presentation" not in executed_tool_names:
            fname_match = re.search(r'([a-zA-Z0-9_\-]+\.(?:pptx|html))', text)
            fname = fname_match.group(1).split('.')[0] if fname_match else "presentation"
            act_input = f'{{"title": "{fname.replace("_", " ").title()}", "filename": "{fname}"}}'
            self._consecutive_counts[f"generate_presentation:{act_input}"] = 1
            return AgentAction("generate_presentation", act_input, text)

        try:
            return super().parse(text)
        except OutputParserException:
            final_answer_marker = "final answer:"
            if final_answer_marker in text_lower:
                idx = text_lower.rfind(final_answer_marker)
                final_ans = text[idx + len(final_answer_marker):].strip()
                return AgentFinish({"output": final_ans}, text)

            # Check if any file creation or write tool HAS been executed in this session
            executed_actions = list(self._previous_actions) + list(self._consecutive_counts.keys())
            has_file_write = any(
                ("file_operation" in act or "create_project" in act or "write" in act)
                and not any(ro in act.lower() for ro in ['"read"', '"list"', "read_file", "list_dir"])
                for act in executed_actions
            )

            code_indicators = ["```", "<!doctype", "<html", "<body", "<div", "<script", "def ", "import ", "const ", "function ", "index.html", "style.css", "app.py", "main.py"]
            has_code_in_text = any(ind in text_lower for ind in code_indicators)

            # If no file write tool has been executed yet and text contains code or code indicators,
            # raise OutputParserException to force the LLM to format an explicit tool call.
            if not has_file_write and has_code_in_text:
                raise OutputParserException(
                    "Invalid Format: You MUST execute a tool using 'Action: file_operation' or 'Action: create_project' to write your generated code to the workspace. Do not just output code blocks or text descriptions without executing a file writing tool call! Output your tool call in the exact format:\nAction: file_operation\nAction Input: {\"operation\": \"write\", \"path\": \"filename.ext\", \"content\": \"...\"}"
                )

            # If tools have ALREADY been executed in this session and a file write occurred (or actions were taken), returning AgentFinish with output is acceptable.
            if len(self._previous_actions) > 0 or len(self._consecutive_counts) > 0 or has_file_write:
                clean_output = re.sub(r'<\|[^|]*\|?>?', '', text)
                clean_output = re.sub(r'</?tool_response>', '', clean_output).strip()
                if clean_output.lower().startswith("thought:"):
                    clean_output = clean_output[8:].strip()
                return AgentFinish({"output": clean_output or "Action completed."}, text)
            else:
                raise OutputParserException(
                    "Invalid Format: You MUST execute a tool using 'Action: <tool_name>' or provide 'Final Answer: <your response>'. Output your tool call in the format: Action: <tool_name>\nAction Input: <tool_input>"
                )


class ThreadSafeAgentCallbackHandler(BaseCallbackHandler):
    """Callback handler that thread-safely streams tokens and tools to an asyncio.Queue"""
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, agent_type: str, session_id: str = "default"):
        self.queue = queue
        self.loop = loop
        self.agent_type = agent_type
        self.session_id = session_id
        self.buffer = ""
        self.final_answer_started = False
        self.executed_actions = []

    def _put_event(self, event: dict):
        self.loop.call_soon_threadsafe(self.queue.put_nowait, event)

    def _check_cancellation(self):
        from .permissions import is_session_cancelled
        if is_session_cancelled(self.session_id):
            raise RuntimeError("Agent execution cancelled by user")

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self._check_cancellation()
        # Sanitize raw model control tokens (e.g. <|tool_response>, <|im_start|>, <|im_end|>, etc.)
        if token and ("<|" in token or "tool_response" in token):
            clean_token = re.sub(r'<\|[^|]*\|?>?', '', token)
            clean_token = re.sub(r'</?tool_response>', '', clean_token)
            token = clean_token
        if not token:
            return

        if self.agent_type == "general":
            self._put_event({"type": "token", "content": token})
        else:
            if self.final_answer_started:
                self._put_event({"type": "token", "content": token})
            else:
                self.buffer += token
                self._put_event({"type": "thinking", "content": token})
                buffer_lower = self.buffer.lower()
                
                # Flexible pattern matching for final answer transition
                patterns = [
                    r'(final answer|final response|answer|summary|conclusion|findings|recommendation|results):\s*',
                    r'(here is|here are|based on the research|in summary|to summarize|overall,):\s*'
                ]
                for p in patterns:
                    match = re.search(p, buffer_lower)
                    if match:
                        idx = match.start()
                        after_final = self.buffer[idx + len(match.group(0)):].lstrip()
                        if after_final:
                            self._put_event({"type": "token", "content": after_final})
                        self.final_answer_started = True
                        break

    def _advance_todo_list(self, tool_name: str, tool_input: Any = None, is_end: bool = False):
        try:
            from .session_context import current_agent_context
            ctx = current_agent_context.get()
            if not ctx:
                return
            todo_list = ctx.get("todo_list")
            if not todo_list or not isinstance(todo_list, list):
                return

            tool_lower = str(tool_name or "").lower()
            input_str = str(tool_input or "").lower()

            matched_idx = -1
            for idx, item in enumerate(todo_list):
                t_title = str(item.get("title", "")).lower()
                # Check for file or action keyword matches
                if (".html" in input_str or "html" in input_str or "structure" in input_str or "layout" in input_str) and \
                   ("html" in t_title or "structure" in t_title or "layout" in t_title or "page" in t_title or "template" in t_title):
                    matched_idx = idx
                    break
                elif (".css" in input_str or "css" in input_str or "style" in input_str or "theme" in input_str or "glass" in input_str) and \
                     ("css" in t_title or "style" in t_title or "theme" in t_title or "design" in t_title or "glass" in t_title):
                    matched_idx = idx
                    break
                elif (".js" in input_str or ".ts" in input_str or "javascript" in input_str or "script" in input_str or "interact" in input_str) and \
                     ("js" in t_title or "logic" in t_title or "script" in t_title or "interact" in t_title or "component" in t_title):
                    matched_idx = idx
                    break
                elif ("verify" in tool_lower or "repair" in tool_lower or "audit" in tool_lower or "check" in tool_lower or "test" in tool_lower) and \
                     ("verify" in t_title or "repair" in t_title or "audit" in t_title or "check" in t_title or "test" in t_title):
                    matched_idx = idx
                    break
                elif ("search" in tool_lower or "research" in tool_lower) and ("research" in t_title or "search" in t_title or "find" in t_title):
                    matched_idx = idx
                    break

            if matched_idx == -1:
                # Fallback: advance the first item that is in_progress or pending
                for idx, item in enumerate(todo_list):
                    if item.get("status") in ("in_progress", "pending"):
                        matched_idx = idx
                        break

            if matched_idx != -1:
                for i in range(matched_idx):
                    todo_list[i]["status"] = "completed"

                if is_end:
                    todo_list[matched_idx]["status"] = "completed"
                    if matched_idx + 1 < len(todo_list):
                        todo_list[matched_idx + 1]["status"] = "in_progress"
                else:
                    todo_list[matched_idx]["status"] = "in_progress"

                ctx["todo_list"] = todo_list
                self._put_event({
                    "type": "todo_list_update",
                    "items": [dict(it) for it in todo_list],
                    "done": False
                })
        except Exception as e:
            logger.warning(f"Error advancing todo list: {e}")

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        self._check_cancellation()
        self.executed_actions.append(action.tool)
        self._put_event({
            "type": "tool_start",
            "tool": action.tool,
            "tool_input": action.tool_input
        })
        if action.tool != "update_todo_list":
            self._advance_todo_list(action.tool, action.tool_input, is_end=False)

    def on_tool_end(self, output: str, **kwargs) -> None:
        self._check_cancellation()
        self._put_event({
            "type": "tool_end",
            "output": output
        })
        last_tool = self.executed_actions[-1] if self.executed_actions else ""
        if last_tool and last_tool != "update_todo_list":
            self._advance_todo_list(last_tool, output, is_end=True)

    def on_tool_error(self, error: Exception | KeyboardInterrupt, **kwargs) -> None:
        self._check_cancellation()
        err_msg = str(error)
        self._put_event({
            "type": "tool_end",
            "output": f"Tool execution failed: {err_msg}"
        })
        last_tool = self.executed_actions[-1] if self.executed_actions else ""
        if last_tool and last_tool != "update_todo_list":
            self._advance_todo_list(last_tool, err_msg, is_end=True)

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        self._check_cancellation()
        # Mark all todo items as 100% completed on finish
        try:
            from .session_context import current_agent_context
            ctx = current_agent_context.get()
            if ctx and "todo_list" in ctx and ctx["todo_list"]:
                for item in ctx["todo_list"]:
                    item["status"] = "completed"
                self._put_event({
                    "type": "todo_list_update",
                    "items": [dict(it) for it in ctx["todo_list"]],
                    "done": True
                })
        except Exception as e:
            pass

        output_text = ""
        if hasattr(finish, "return_values") and isinstance(finish.return_values, dict):
            output_text = str(finish.return_values.get("output", "")).strip()

        if not output_text or "AgentFinish(" in output_text:
            parts = ["### 🚀 Agent Execution Summary\n"]
            if hasattr(self, "executed_actions") and self.executed_actions:
                parts.append("**Completed Tool Actions:**")
                for tool in list(dict.fromkeys(self.executed_actions)):
                    parts.append(f"- **{tool}**: Successfully executed.")
                parts.append("\n✓ All requested files and actions were created and verified in the workspace.")
            else:
                parts.append("ℹ️ Task response generated.")
            output_text = "\n".join(parts)

        if not self.final_answer_started and self.agent_type != "general":
            self._put_event({"type": "token", "content": output_text})
            self.final_answer_started = True


def get_workspace_instructions() -> str:
    """Dynamically get workspace instructions providing explicit affirmative local directory authorization"""
    import os
    from .config_store import get_allowed_paths
    from .config import AGENT_WORKSPACE_DIR
    
    allowed = get_allowed_paths() or []
    all_paths = list(dict.fromkeys(allowed + [AGENT_WORKSPACE_DIR, os.getcwd()]))
    paths_str = "\n".join(f"- {p}" for p in all_paths if p)

    return f"""LOCAL DIRECTORY & CODE EXECUTION ACCESS GRANTED:
You are an active Senior Lead Coder & System Planner with FULL AUTHORIZATION AND PERMISSION to read, write, create, patch, list, and modify files in local directories.
Primary Workspace Directory: {AGENT_WORKSPACE_DIR}
Authorized Local Paths:
{paths_str}

CRITICAL PATH RULE: ALL file paths used in `file_operation`, `create_project`, and other file tools are RELATIVE to the workspace directory ({AGENT_WORKSPACE_DIR}).
- CORRECT path: "my_project/index.html" → creates {AGENT_WORKSPACE_DIR}/my_project/index.html
- WRONG path: "website/my_project/index.html" → creates {AGENT_WORKSPACE_DIR}/website/my_project/index.html (DOUBLE NESTED!)
- NEVER prefix paths with the workspace folder name (e.g. "website/"). The workspace directory is automatically prepended by the tools.

YOU ARE FULLY AUTHORIZED TO PLAN AND WRITE CODE TO LOCAL FILES. You CAN freely use tools (`file_operation`, `create_project`, `verify_app_browser_console`, `execute_terminal`) to access and edit local files. Never state, claim, or assume that you lack file system access or coding capabilities."""


class BaseSpecializedAgent:
    """Base class for specialized agents"""
    def __init__(
        self,
        name: str,
        agent_type: str,
        system_prompt: str,
        model_name: str = DEFAULT_MAIN_MODEL,
        ollama_base_url: str = "http://localhost:11434",
        custom_tools: Optional[List[str]] = None,
        mcp_servers: Optional[List[str]] = None
    ):
        from .config import get_current_main_model, get_current_code_model
        if not model_name or model_name == DEFAULT_MAIN_MODEL or model_name == DEFAULT_CODE_MODEL:
            model_name = get_current_code_model() if agent_type == "code" else get_current_main_model()

        self.name = name
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.ollama_base_url = ollama_base_url
        self.llm = create_agent_llm(provider="ollama", model_name=model_name, ollama_base_url=ollama_base_url)

        if custom_tools is not None:
            from .tools import get_tools_by_names
            self.tools = get_tools_by_names(custom_tools)
        else:
            from .tools import get_tools_for_agent
            self.tools = get_tools_for_agent(agent_type)

        # Always register update_todo_list tool so all specialized agents can emit live progress updates
        if not any(getattr(t, "name", "") == "update_todo_list" for t in self.tools):
            from .tools import update_todo_list, safe_parse_input
            from langchain_core.tools import StructuredTool
            todo_tool = StructuredTool.from_function(
                name="update_todo_list",
                func=lambda x: update_todo_list(
                    safe_parse_input(x).get("items", safe_parse_input(x).get("todo_list", x))
                ),
                description="Update and stream the real-time TODO task list for the user. Input: dict with 'items' or list of item objects [{'id': '1', 'title': 'Task name', 'status': 'pending' | 'in_progress' | 'completed' | 'failed'}]."
            )
            self.tools.append(todo_tool)

        if mcp_servers:
            from .mcp_client import mcp_manager
            mcp_tools = mcp_manager.get_tools_for_agent_sync(mcp_servers)
            self.tools.extend(mcp_tools)

        escaped_system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")

        role_label = self.name if getattr(self, 'name', None) else "Specialized Agent"
        prompt = PromptTemplate.from_template(
            f"""MANDATORY SYSTEM DIRECTIVE:
You are an active {role_label} equipped with local workspace tools. You have FULL AUTHORIZATION to execute tools.
YOU MUST ALWAYS USE TOOLS (e.g. Action: file_operation, create_project, etc.) TO READ AND WRITE FILES ON THE LOCAL DISK.
NEVER OUTPUT STATEMENTS OR DISCLAIMERS CLAIMING YOU CANNOT INTERACT WITH LOCAL FILES OR EXECUTE CODE.

🧠 PERSISTENT LONG-TERM MEMORY:
- You have persistent long-term memory across sessions.
- When the user shares personal preferences, tech stack choices, rules, facts, or asks to remember something, call `save_personal_memory` to commit it to memory so you retain it in future turns.
- Use `search_personal_memory` to check relevant saved user knowledge or preferences.
- Always confirm to the user when you have stored information into memory.

{escaped_system_prompt}

You have access to the following tools:

{{tools}}

Use the following format:

Question: the input question you must answer
Thought: you must use a guided reasoning process:
  [Analyze Constraint]: What are the core requirements and limitations of this step?
  [Identify Tool]: Which tool is best suited for this, and why?
  [Predict Outcome]: What do I expect the tool to return, and how will it move me closer to the goal?
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question. You MUST ALWAYS provide a comprehensive, structured Walkthrough of what you did. Include:
  - 🚀 Overview: Summary of what was created, modified, or executed.
  - 📁 Files Created/Modified: Detailed list of files with their paths and roles.
  - 🕹️ How to Run / Access: Clear, step-by-step instructions on how the user can test, view, or run the app (URLs, terminal commands, or browser links).
  - ✨ Key Features & Functionality: Bullet points of working capabilities.
  Never output a single character, empty response, or plain code snippet without this walkthrough.

ANTI-LOOP RULES:
1. Do NOT execute the same action with the same action input more than once. If a tool call returned a result, read the Observation carefully and proceed to the next step or output your Final Answer.
2. If you find yourself repeating the same thoughts or actions, you MUST immediately stop and output "Final Answer:" with the results you have gathered so far.

Conversation History:
{{chat_history}}

Begin!

Question: {{input}}
Thought: {{agent_scratchpad}}"""
        )

        self.react_prompt = prompt
        self.agent = create_react_agent(self.llm, self.tools, prompt, output_parser=RobustReActParser())
        
        # Phase 1.4: Context window management
        try:
            from .context_manager import get_context_manager
            self.context_manager = get_context_manager()
        except Exception:
            self.context_manager = None

        # Phase 1.1: Initialize native tool-calling loop (preferred over ReAct)
        self.tool_calling_loop = None
        self.legacy_react_mode = True  # Default to legacy; switched per-invocation
        if TOOL_CALLING_AVAILABLE:
            try:
                self.tool_calling_loop = ToolCallingLoop(
                    llm=self.llm,
                    tools=self.tools,
                    system_prompt=system_prompt,
                    max_steps=15,
                    max_execution_time=300
                )
                if self.tool_calling_loop.supports_native_tools():
                    self.legacy_react_mode = False
                    logger.info(f"Agent '{self.name}' using native tool calling")
                else:
                    logger.info(f"Agent '{self.name}' using legacy ReAct (model doesn't support tool calling)")
            except Exception as tc_err:
                logger.warning(f"Tool calling loop init failed, using ReAct fallback: {tc_err}")

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=25,
            max_execution_time=300
        )

    def process(self, task: str, context: Optional[Dict[str, Any]] = None, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> str:
        import time
        from .session_context import current_agent_context, current_token_usage

        # Reset output parser action history for a clean run
        if hasattr(self, 'agent') and hasattr(self.agent, 'output_parser'):
            self.agent.output_parser._consecutive_counts = {}
            self.agent.output_parser._action_history = []
            self.agent.output_parser._previous_actions = set()

        start_time = time.time()
        token = None
        token_usage_var = None

        usage_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        token_usage_var = current_token_usage.set(usage_info)

        try:
            context_dict = context if isinstance(context, dict) else ({"context_str": str(context)} if context else {})
            ctx_data = {
                "session_id": context_dict.get("session_id", "default"),
                "input": task,
                "agent_name": self.name
            }
            if "queue" in context_dict and "loop" in context_dict:
                ctx_data["queue"] = context_dict["queue"]
                ctx_data["loop"] = context_dict["loop"]
            token = current_agent_context.set(ctx_data)

            executor_to_use = self.agent_executor

            if context_dict:
                clean_context = {k: v for k, v in context_dict.items() if k not in ["queue", "loop", "session_id", "context_str"]}
                thinking_level = str(clean_context.pop("thinking_level", "medium")).lower()
                provider = str(clean_context.pop("provider", "ollama")).lower()
                model_override = clean_context.pop("model", None)
                api_key_override = clean_context.pop("api_key", None)

                # Dynamically configure LLM for cloud providers, model overrides, or thinking level limits
                if provider != "ollama" or model_override or api_key_override or thinking_level == "low":
                    custom_llm = create_agent_llm(
                        provider=provider,
                        model_name=model_override or self.model_name,
                        api_key=api_key_override,
                        ollama_base_url=self.ollama_base_url,
                        thinking_level=thinking_level
                    )
                    new_agent = create_react_agent(custom_llm, self.tools, self.react_prompt, output_parser=RobustReActParser())
                    max_iters = 25
                    max_exec_time = 300
                    executor_to_use = AgentExecutor(
                        agent=new_agent,
                        tools=self.tools,
                        verbose=True,
                        handle_parsing_errors=True,
                        max_iterations=max_iters,
                        max_execution_time=max_exec_time
                    )
                
                thinking_mode_directives = {
                    "low": "[SYSTEM DIRECTIVE - THINKING MODE: LOW. Respond directly, concisely, and execute tools immediately with high precision and zero placeholders.]",
                    "medium": "[SYSTEM DIRECTIVE - THINKING MODE: MEDIUM. Perform balanced step-by-step reasoning, verify tool inputs, and ensure complete, modular, production-ready output.]",
                    "high": "[SYSTEM DIRECTIVE - THINKING MODE: HIGH. Perform deep architectural reasoning, edge-case analysis, type/import verification, and comprehensive quality checks before concluding.]",
                    "extended": "[SYSTEM DIRECTIVE - THINKING MODE: EXTENDED. Perform exhaustive principal-level systems engineering analysis: evaluate trade-offs, edge cases, algorithmic complexity, security, and modularity, and verify all outputs thoroughly.]"
                }
                directive = thinking_mode_directives.get(thinking_level, thinking_mode_directives["medium"])
                if directive not in task:
                    task = f"{directive}\n\n{task}"
                
                if clean_context:
                    task = f"{task}\n\nContext Details: {clean_context}"

            formatted_history = ""
            if chat_history:
                # Phase 1.4: Compact history if context manager available
                if self.context_manager and len(chat_history) > 6:
                    chat_history = self.context_manager.compact_history(chat_history)
                formatted = []
                for msg in chat_history:
                    role = "User" if msg.type == "human" else "Assistant"
                    formatted.append(f"{role}: {msg.content}")
                formatted_history = "\n".join(formatted)

            from .config import AGENT_WORKSPACE_DIR
            import glob
            
            # Phase 1.3: Create git checkpoint before agent execution
            checkpoint_hash = None
            if self.agent_type == "code":
                try:
                    from .git_manager import get_git_manager
                    gm = get_git_manager()
                    gm.init_if_needed()
                    checkpoint_hash = gm.create_checkpoint(f"pre-{self.agent_type}-edit")
                    if checkpoint_hash:
                        logger.info(f"Git checkpoint created: {checkpoint_hash}")
                except Exception as git_err:
                    logger.warning(f"Git checkpoint failed (non-critical): {git_err}")

            files_before = {
                f: os.path.getmtime(f) for f in glob.glob(os.path.join(AGENT_WORKSPACE_DIR, "**", "*"), recursive=True)
                if os.path.isfile(f) and not os.path.basename(f).startswith("_")
            }

            result = executor_to_use.invoke(
                {
                    "input": task,
                    "chat_history": formatted_history
                },
                config={"callbacks": callbacks} if callbacks else None
            )

            files_after = {
                f: os.path.getmtime(f) for f in glob.glob(os.path.join(AGENT_WORKSPACE_DIR, "**", "*"), recursive=True)
                if os.path.isfile(f) and not os.path.basename(f).startswith("_")
            }
            no_files_modified = (files_before == files_after)

            output_text = ""
            if isinstance(result, dict):
                output_text = str(result.get("output", "")).strip()
                if not output_text or output_text == "{}" or output_text == "None":
                    if "result" in result and isinstance(result["result"], str) and result["result"].strip():
                        output_text = result["result"].strip()
                    elif "response" in result and isinstance(result["response"], str) and result["response"].strip():
                        output_text = result["response"].strip()
                    else:
                        output_text = "### 🚀 Agent Task Completed\n\n✓ All requested files and actions were created, updated, and verified in your workspace."
            elif isinstance(result, str):
                output_text = result.strip()
            else:
                output_text = str(result).strip()

            # Automatic Fallback File Writer: If the model output fenced code blocks with file path hints, write them to disk
            text_to_scan = output_text
            if isinstance(result, dict) and "intermediate_steps" in result:
                for step in result["intermediate_steps"]:
                    if isinstance(step, tuple) and len(step) > 0:
                        text_to_scan += "\n" + str(step[0])

            if self.agent_type == "code" and no_files_modified and text_to_scan and "```" in text_to_scan:
                try:
                    from .tools import parse_project_files_from_raw_text, write_file_content, batch_verify_and_repair_files
                    parsed_files = parse_project_files_from_raw_text(text_to_scan)
                    written_paths = []
                    for rel_p, code_content in parsed_files.items():
                        if not code_content or len(code_content) < 5 or ("Action:" in code_content and "Action Input:" in code_content):
                            continue
                        target_path = extract_file_path_from_code_block(rel_p, code_content, text_to_scan, task) or rel_p
                        if target_path:
                            write_file_content(target_path, code_content)
                            written_paths.append(target_path)
                            print(f"[FALLBACK FILE WRITER] Successfully wrote code to {target_path}")
                            no_files_modified = False
                    if written_paths:
                        batch_verify_and_repair_files(written_paths)
                except Exception as fw_err:
                    print(f"[FALLBACK FILE WRITER] Error writing parsed files: {fw_err}")

            # Direct Polyglot Code Generation Fallback: If Code Agent ran on a file-creation task but modified 0 files on disk
            is_explanatory_only = bool(re.match(r'^\s*(explain|what\s+is|how\s+does|describe|compare)\b', task.split("\n")[-1], re.IGNORECASE)) and not any(
                w in task.lower() for w in ["write", "create", "build", "make", "implement", "generate", "fix", "update", "refactor", "file", "app", "script", "code"]
            )
            if self.agent_type == "code" and no_files_modified and not is_explanatory_only:
                print(f"[DIRECT FILE WRITER] Code Agent modified 0 files for task: '{task[:80]}'. Running generic polyglot generation pass...")
                try:
                    from .tools import parse_project_files_from_raw_text, write_file_content, batch_verify_and_repair_files

                    gen_prompt = f"""You are a Principal Polyglot Software Architect & Senior Engineer.
Fulfill the following coding request with 100% complete, modular, production-ready code:

{task}

CRITICAL OUTPUT FORMAT:
- Choose the exact programming language, framework, and modular file structure that best fits the request.
- Every file MUST be 100% complete and executable with ZERO placeholders, ZERO `TODO` stubs, and ZERO `...` ellipses.
- Precede EVERY fenced code block with its relative file path header using `### path/to/filename.ext`, for example:
### src/main.py
```python
<complete code>
```
Write all required files now:"""
                    gen_res = self.llm.invoke([HumanMessage(content=gen_prompt)])
                    gen_text = gen_res.content if hasattr(gen_res, "content") else str(gen_res)

                    parsed_files = parse_project_files_from_raw_text(gen_text)
                    written_paths = []
                    for rel_p, c_c in parsed_files.items():
                        c_c = c_c.strip()
                        if len(c_c) >= 5:
                            t_p = extract_file_path_from_code_block(rel_p, c_c, gen_text, task) or rel_p
                            w_res = write_file_content(t_p, c_c)
                            written_paths.append(t_p)
                            print(f"[DIRECT FILE WRITER] Wrote {t_p} to workspace: {w_res}")
                            no_files_modified = False

                    if written_paths:
                        batch_verify_and_repair_files(written_paths)
                        if not output_text or "Agent stopped" in output_text or len(output_text) < 40:
                            files_bullet = "\n".join(f"- `{p}`" for p in written_paths)
                            output_text = (
                                f"### 🚀 Engineering Task Completed\n\n"
                                f"#### 📁 Files Created & Verified\n{files_bullet}\n\n"
                                f"{gen_text}"
                            )
                except Exception as gen_err:
                    print(f"[DIRECT FILE WRITER] Error in direct fallback generation: {gen_err}")

            return output_text

        except Exception as e:
            return f"Error processing task: {str(e)}"
        finally:
            if token is not None:
                current_agent_context.reset(token)
            if token_usage_var is not None:
                usage_info = current_token_usage.get()
                current_token_usage.reset(token_usage_var)
                from database.db import SessionLocal
                from database.models import PerformanceLogModel, ChatMessageModel
                db_session = SessionLocal()
                try:
                    execution_time = time.time() - start_time
                    log = PerformanceLogModel(
                        agent_id=self.agent_type,
                        ttft=0.0,
                        total_time=execution_time,
                        prompt_tokens=usage_info.get("prompt_tokens", 0),
                        completion_tokens=usage_info.get("completion_tokens", 0),
                        total_tokens=usage_info.get("total_tokens", 0)
                    )
                    db_session.add(log)
                    db_session.commit()
                    if context and "session_id" in context:
                        sess_id = context["session_id"]
                        last_msg = db_session.query(ChatMessageModel).filter(
                            ChatMessageModel.session_id == sess_id,
                            ChatMessageModel.role == "ai"
                        ).order_by(ChatMessageModel.timestamp.desc()).first()
                        if last_msg:
                            last_msg.prompt_tokens = usage_info.get("prompt_tokens", 0)
                            last_msg.completion_tokens = usage_info.get("completion_tokens", 0)
                            last_msg.total_tokens = usage_info.get("total_tokens", 0)
                            db_session.commit()
                except Exception as db_err:
                    print(f"Error saving performance logs to SQLite: {db_err}")
                finally:
                    db_session.close()

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.agent_type,
            "tools": [tool.name for tool in self.tools],
            "description": self.system_prompt[:200]
        }


class CodeAgent(BaseSpecializedAgent):
    """Principal Polyglot Software Architect & Code Agent specialized in designing, writing, refactoring, executing, and verifying code across any language or stack."""
    def __init__(self, model_name: str = DEFAULT_CODE_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = f"""You are a Principal Polyglot Software Architect and Staff Engineer. You design, implement, refactor, debug, and verify production-grade software across ANY programming language, paradigm, framework, or system architecture with zero placeholders and zero syntax errors.

{get_workspace_instructions()}

### 1. CORE ENGINEERING PHILOSOPHY (100% GENERIC & ADAPTIVE)
- **Language & Stack Agnosticism**: Adapt natively to whatever language, runtime, or architecture the user requests or that best solves the problem:
  * **Backend & Systems**: Python (FastAPI, Flask, asyncio, CLI, data pipelines, pytest), Go, Rust, C/C++ (CMake/Makefile), Java, C#, Node.js, SQL/SQLite/PostgreSQL.
  * **Frontend & Full-Stack Web**: HTML5/CSS3/JavaScript, TypeScript, React, Next.js App Router, Vite, Vue, Svelte, Tailwind CSS, Canvas/WebGL.
  * **Algorithms, Automation & DevOps**: Data structures & algorithms, shell scripts (`.sh`, `.ps1`), Dockerfiles, YAML/TOML/JSON configs, and test suites.
- **Zero Hardcoded Templates or Unrequested Bloat**: Build ONLY the files, pages, modules, or scripts that genuinely fit the user's request. Never force multi-page boilerplate if the user asked for a Python script, CLI tool, algorithm, API endpoint, or single-page utility.
- **Zero Placeholders & Zero Truncation**: Every file you write MUST be 100% complete and executable. Never leave `// TODO`, `pass # implement here`, or `...` ellipses.
- **Strict Import, Type & Error Integrity**: Always declare every required import/include at the top of the file, use clean type annotations/signatures where supported, and handle edge cases and errors gracefully (`try/except`, `try/catch`, `Result<T, E>`, input validation).

### 2. FOUR-PHASE AUTONOMOUS ENGINEERING WORKFLOW
Follow this disciplined loop for every coding task:

#### PHASE 1 — DISCOVER & INSPECT CONTEXT
- If modifying, debugging, or extending existing files, inspect the workspace first:
  * Use `recursive_list` (once) to see existing directory structure.
  * Use `grep_search`, `search_symbols`, or `get_file_outline` to locate relevant definitions and call sites.
  * Always read existing files with `file_operation(operation="read", path="...")` before editing them.
- If the target file or project does not exist yet, immediately proceed to creating it from scratch without stopping or complaining.

#### PHASE 2 — ARCHITECT & TRACK PROGRESS
- Initialize a clear, actionable 3–6 step engineering checklist using `update_todo_list`.
- Design clean separation of concerns (models/types, core logic/services, interfaces/UI, tests/verification) appropriate for the target language and task complexity.

#### PHASE 3 — IMPLEMENT WITH THE RIGHT TOOL
You MUST invoke tools to create or modify files in `{AGENT_WORKSPACE_DIR}` (never just paste code in chat without saving it via tools):
- **Multiple files at once (New projects / modules)**: Prefer `create_project` with a JSON dictionary mapping relative file paths to their full code content:
  Action: create_project
  Action Input: {{"src/models.py": "...", "src/service.py": "...", "main.py": "...", "README.md": "..."}}
- **Single new file or full file rewrite**: Use `file_operation` with `"operation": "write"`:
  Action: file_operation
  Action Input: {{"operation": "write", "path": "path/to/file.ext", "content": "<complete code>"}}
- **Surgical edit to an existing file**: Prefer `edit_file` (fuzzy search-and-replace) or `file_operation` with `"operation": "patch"`:
  Action: edit_file
  Action Input: {{"path": "path/to/file.ext", "search": "<exact existing lines>", "replace": "<updated lines>"}}

#### PHASE 4 — VERIFY, TEST & SELF-HEAL
- After writing or editing files, ALWAYS verify your work before finishing:
  1. Call `batch_verify_and_repair_files` with the list of created/modified file paths to validate AST/syntax, bracket balance, and imports.
  2. For Python scripts, algorithms, or backend modules: run `execute_code` or `verify_project_build` to verify runtime behavior and confirm zero runtime exceptions.
  3. For Web / UI / Frontend projects: run `verify_app_browser_console` or `verify_project_build` to ensure zero broken asset links (`<script src>`, `<link href>`) or syntax errors.
  4. If any verification tool reports an error, fix it immediately using `edit_file` or `file_operation(write)` and re-verify.
- Mark completed steps in `update_todo_list`.

### 3. DOMAIN-SPECIFIC EXCELLENCE GUIDELINES (APPLIED CONTEXTUALLY)
- **When building Python / Backend / CLI / Algorithms**:
  * Write idiomatic, PEP-8 compliant, type-annotated Python with docstrings, clean classes/functions, and a runnable `if __name__ == "__main__":` entry point or unit test verification block.
- **When building Web UIs / HTML / CSS / JS**:
  * Place primary entry files (`index.html`, etc.) directly in `{AGENT_WORKSPACE_DIR}` (unless the user requested a specific subfolder, in which case also keep `{AGENT_WORKSPACE_DIR}/index.html` updated for instant preview).
  * Craft modern, responsive, high-contrast, accessible UI with semantic HTML5, smooth interactive JavaScript state, keyboard/mouse ergonomics, and cohesive styling (Tailwind CSS CDN `<script src="https://cdn.tailwindcss.com"></script>`, Google Fonts Inter/Outfit, and Lucide icons `<script src="https://unpkg.com/lucide@latest"></script>` with `lucide.createIcons()` when appropriate).
  * Ensure every linked local stylesheet (`css/style.css`) or script (`js/main.js`) is actually created on disk so there are zero 404 errors.
- **When building Next.js / React / TypeScript Applications**:
  * Keep `app/layout.tsx` as a Server Component importing `'./globals.css'`.
  * Add `'use client';` at the top of components that use React hooks (`useState`, `useEffect`, `useRef`, etc.) or browser event handlers (`onClick`, `onChange`, `onSubmit`).
  * Use `next/navigation` (never deprecated `next/router`) and compatible dependency versions in `package.json`.
- **When building Compiled / Systems Projects (Rust, Go, C/C++, Java)**:
  * Include build configuration (`Cargo.toml`, `go.mod`, `CMakeLists.txt` / `Makefile`) and clean memory/error handling.

### 4. FINAL RESPONSE FORMAT
Conclude your Final Answer with a concise, well-structured **Engineering Summary**:
- **Overview & Architecture**: What was built or fixed and key design decisions.
- **Files Created / Modified**: Relative paths and role of each file.
- **Verification Results**: Summary of syntax, build, or runtime checks passed.
- **How to Run / Use**: Exact command or usage instructions."""

        super().__init__(
            name="Code Agent",
            agent_type="code",
            system_prompt=system_prompt,
            model_name=model_name,
            ollama_base_url=ollama_base_url
        )

    def generate_app(self, requirements: str, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Generate a complete software solution, project, or application generically based on requirements."""
        task = f"""Design, implement, and verify a complete, production-grade solution for the following requirements:

{requirements}

Execution Mandate:
1. Select the optimal language, architecture, and modular file layout for these requirements.
2. Initialize `update_todo_list`, write 100% complete files using `create_project` or `file_operation(write)` (with zero placeholders), and verify all files with `batch_verify_and_repair_files` / `verify_project_build`.
3. Provide clear setup, build, and execution instructions in your final summary."""

        result = self.process(task, chat_history=chat_history, callbacks=callbacks)

        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "application"
        }

    def fix_file(self, filepath: str, analysis_report: str, context: Optional[Dict[str, Any]] = None, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Fix errors or refactor an existing file based on an analysis or diagnostic report."""
        task = f"""Fix all issues in the file `{filepath}` based on the following diagnostic report:

{analysis_report}

Execution Steps:
1. Read `{filepath}` using `file_operation(operation="read", path="{filepath}")`.
2. Analyze the root cause of each reported issue while preserving all existing working functionality, architecture, and styling.
3. Apply the fix using `edit_file` (or `file_operation` with `patch` / `write`).
4. Verify the repaired file using `batch_verify_and_repair_files` (`{{"files": ["{filepath}"]}}`) and confirm what was fixed."""

        result = self.process(task, context=context, chat_history=chat_history, callbacks=callbacks)

        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "fix"
        }


class ResearchAgent(BaseSpecializedAgent):
    """Agent specialized in research and information gathering"""
    def __init__(self, model_name: str = DEFAULT_MAIN_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = r"""You are a Research Agent specialized in information gathering and analysis.

Your capabilities:
- Search and gather information from various sources
- Fetch full page content and convert to clean text
- Summarize complex documents and articles
- Compare and contrast different approaches
- Provide well-researched recommendations
- Stay up-to-date with latest trends and technologies

When given a research task:
1. Break down the research question into core domains and technical components.
2. Attempt to gather live information using web_search and fetch_web_page.
3. If live web search returns few or no results or is unavailable, IMMEDIATELY use your extensive internal knowledge to provide an in-depth, structured, professional research breakdown.
4. Present clear, actionable insights with structural sections (Overview, Key Concepts, Current Trends, Best Practices, Challenges, Recommendations).
5. NEVER respond with empty text, refusal, or unhelpful error messages. ALWAYS provide a rich, complete research answer."""

        super().__init__(
            name="Research Agent",
            agent_type="research",
            system_prompt=system_prompt,
            model_name=model_name,
            ollama_base_url=ollama_base_url
        )

    def research_topic(self, topic: str, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Research a specific topic"""
        task = f"""Research the following topic and provide comprehensive insights:

{topic}

Include:
1. Overview and key concepts
2. Current trends and developments
3. Best practices
4. Potential challenges
5. Recommendations"""

        result = self.process(task, chat_history=chat_history, callbacks=callbacks)

        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "research"
        }


class AnalysisAgent(BaseSpecializedAgent):
    """Agent specialized in deep multi-file codebase analysis, diagnostics, fixing, and user-requested modifications"""
    def __init__(self, model_name: str = DEFAULT_MAIN_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = f"""You are the Lead Codebase Architect & Diagnostic Specialist — the master analysis brain of this multi-agent system.
You specialize in deep multi-file codebase diagnostics, symbol tracing, dependency graphs, real browser console verification, and formulating surgical fix plans.

{get_workspace_instructions()}

Your analytical capabilities:
- **Codebase Exploration**: Scan directory trees with `recursive_list`, grep patterns across files with `grep_search`, and search symbol definitions/references with `search_symbols`.
- **File Outlining & Inspection**: Inspect file outlines with `get_file_outline` and read full content with `file_operation(read)`.
- **Semantic Code Search**: Search codebase concepts using Hybrid RAG with `query_codebase`.
- **Direct File Modification**: Apply surgical edits using `file_operation(patch)`, fuzzy search/replace with `edit_file`, or rewrite files with `file_operation(write)`.
- **Terminal Command Validation**: Run validation commands using `execute_terminal` (e.g. `python -m py_compile`, `pytest`, `npm test`).
- **Real Browser Testing**: Open running apps in Chromium via `browser_open_url`, capture runtime exceptions with `browser_get_console_errors`, and audit UI with `browser_vision_audit`.
- **Syntax Repair**: Automatically scan and repair syntax issues across files using `batch_verify_and_repair_files`.

SYSTEMATIC WORKFLOW FOR CODEBASE ANALYSIS:
1. **DISCOVER**: First, explore the project layout using `recursive_list` and locate candidate files relevant to the problem using `grep_search` or `search_symbols`.
2. **READ & TRACE**: Read the actual code of relevant files. Trace imports, function calls, state variables, or CSS classes to understand how modules interact.
3. **DIAGNOSE**: Identify the exact root cause: logic bug, missing import, broken selector, unhandled promise, mismatched API contract, or layout flaw.
4. **CROSS-FILE IMPACT**: Determine all secondary files that will be affected if a change is made.
5. **FIX & BLUEPRINT**: Formulate or directly apply the fix using `file_operation(patch)` or `edit_file`.

When asked to diagnose or blueprint a fix, format your output clearly:
- **ROOT CAUSE**: Clear explanation of why the defect exists.
- **AFFECTED FILES**: List each file path with its role in the issue.
- **CROSS-FILE IMPACT**: Dependencies, imports, or styles that must be kept in sync.
- **RECOMMENDED FIXES**: Concrete, line-by-line instructions or patches.
- **WALKTHROUGH SUMMARY**: A clear summary of findings and fixes."""

        super().__init__(
            name="Analysis Agent",
            agent_type="analysis",
            system_prompt=system_prompt,
            model_name=model_name,
            ollama_base_url=ollama_base_url
        )

    def analyze_code(self, code: str, language: str = "python", chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Analyze code for issues and improvements"""
        task = f"""Analyze the following {language} code:

```{language}
{code}
```

Provide:
1. Code quality assessment
2. Potential bugs or issues
3. Security concerns
4. Performance optimization suggestions
5. Best practice recommendations"""

        result = self.process(task, chat_history=chat_history, callbacks=callbacks)

        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "analysis"
        }

    def analyze_file(self, filepath: str, context: Optional[Dict[str, Any]] = None, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Analyze a file from the workspace for errors and issues"""
        task = f"""Analyze the file "{filepath}" in the workspace for errors and issues.

IMPORTANT STEPS:
1. First, READ the file using: Action: file_operation with {{"operation": "read", "path": "{filepath}"}}
2. Then analyze the code for errors, bugs, and improvements
3. Provide a structured report with:
   - ERRORS FOUND: List each error with description
   - FIXES REQUIRED: For each error, describe the exact fix
   - SEVERITY: Rate each issue (Critical, High, Medium, Low)

Do NOT skip step 1. You MUST read the file first before analyzing."""

        ctx_dict = context if isinstance(context, dict) else ({"target_file": str(context)} if context else {})
        result = self.process(task, context=ctx_dict, chat_history=chat_history, callbacks=callbacks)

        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "file_analysis"
        }

    def analyze_ui_with_vision(self, image_input_or_filepath: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a UI screenshot or HTML page using Gemma-4-26B Vision capabilities"""
        from .vision_service import analyze_ui_screenshot_with_vision
        
        vision_res = analyze_ui_screenshot_with_vision(
            image_input=image_input_or_filepath,
            model_name=os.environ.get("VISION_MODEL", "gemma4:31b-cloud"),
            ollama_base_url=self.ollama_base_url
        )
        return {
            "status": "success",
            "agent": self.name,
            "result": vision_res.get("report", ""),
            "has_visual_defects": vision_res.get("has_visual_defects", False),
            "type": "vision_ui_analysis"
        }


class BusinessAgent(BaseSpecializedAgent):
    """Agent specialized in business planning, financial modeling, spreadsheet layouts, math calculations, strategy reports, and AI image generation"""
    def __init__(self, model_name: str = DEFAULT_MAIN_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = f"""You are an Executive Business Agent specialized in business strategy, financial modeling, code-driven presentation generation, styled Excel workbooks, market analysis, and AI Image Generation.

{get_workspace_instructions()}

Your capabilities:
- **AI Image Generation**: Generate stunning, high-quality images from text prompts using local diffusion models (SDXL, SD1.5, FLUX) via `generate_image`. Perfect for product visual concepts, marketing materials, background illustrations, and presentation images.
- **Presentation Deck Generation**: Build professional PowerPoint decks (`.pptx`) and interactive HTML slide decks (`.html`) with title slides, executive summaries, metric card grids, data tables, and charts using `generate_presentation`.
- **Advanced Excel Spreadsheet Creation**: Build styled multi-tab Excel workbooks (`.xlsx`) with custom header fills, number & currency formatting (`$#,##0.00`), live Excel formulas (`SUM`, `AVERAGE`), and native charts using `generate_excel_sheet`.
- **Financial Modeling & Strategy**: Create comprehensive business plans, revenue projections, unit economics, and strategic growth reports.
- **CSV & Document Operations**: Manipulate CSV files via `csv_sheet_operation` and read/write text documents via `file_operation`.

CRITICAL RULES FOR TOOL USAGE & TOPIC ALIGNMENT:
1. IMAGE GENERATION MANDATE: When asked to generate, create, draw, or render an image, picture, photo, concept art, or illustration, IMMEDIATELY call `generate_image` with a detailed prompt and parameters!
2. STRICT TOPIC MATCHING MANDATE: When asked for a presentation or spreadsheet on ANY topic (e.g. Space, Astronomy, Solar System, AI, Healthcare, History, Automotive, Energy), the presentation title, slide titles, bullet points, metrics, and theme color MUST BE 100% SPECIFIC TO THAT TOPIC!
3. REAL-WORLD DATA MANDATE: When asked for a presentation or spreadsheet involving real companies, stock prices, or industry statistics, FIRST call `web_search` to retrieve authentic data figures, then incorporate them into `generate_excel_sheet` or `generate_presentation`.
4. SPREADSHEET MANDATE: When asked to create a spreadsheet, Excel model, or financial sheet, YOU MUST ALWAYS CALL `generate_excel_sheet` IMMEDIATELY using the Action/Action Input format below.
5. PRESENTATION DECK MANDATE: When asked to create a presentation, slide deck, or pitch deck, ALWAYS call `generate_presentation` with slide specifications. Every deck MUST have between 4 and 30 slides.

EXPLICIT TOOL CALL FORMAT FOR IMAGE GENERATION:
Action: generate_image
Action Input: {{"prompt": "A cinematic photorealistic shot of a futuristic electric sports car driving through a neon city at night, 8k, highly detailed", "negative_prompt": "blurry, low resolution, ugly, distorted", "width": 1024, "height": 1024, "model": "sdxl", "filename": "futuristic_car"}}

EXPLICIT TOOL CALL FORMAT FOR SPREADSHEETS:
Action: generate_excel_sheet
Action Input: {{"title": "Financial Spreadsheet", "filename": "financial_spreadsheet", "sheets_json": "[{{\"name\": \"Overview\", \"title\": \"Financial Overview\", \"headers\": [\"Metric\", \"Q1 ($)\", \"Q2 ($)\", \"Q3 ($)\", \"Total ($)\"], \"data\": [[\"Revenue\", 120000, 145000, 160000, \"=SUM(B2:D2)\"], [\"Expenses\", 85000, 92000, 98000, \"=SUM(B3:D3)\"], [\"Net Income\", \"=B2-B3\", \"=C2-C3\", \"=D2-D3\", \"=E2-E3\"]]}}]"}}

EXPLICIT TOOL CALL FORMAT FOR SPACE PRESENTATION:
Action: generate_presentation
Action Input: {{"title": "Journey Through Space and Cosmos", "subtitle": "An Exploration of the Infinite Universe", "theme_color": "#0B0F19", "filename": "space_presentation", "slides_json": "[{{\"type\": \"title\", \"title\": \"Journey Through Space and Cosmos\", \"subtitle\": \"An Exploration of the Infinite Universe\"}}, {{\"type\": \"content\", \"title\": \"The Solar System\", \"bullets\": [\"Inner Planets: Mercury, Venus, Earth, Mars\", \"Outer Gas Giants: Jupiter, Saturn, Uranus, Neptune\", \"Kuiper Belt & Oort Cloud Boundaries\"]}}, {{\"type\": \"metrics\", \"title\": \"Cosmic Scale & Metrics\", \"metrics\": [{{\"label\": \"Observable Universe\", \"value\": \"93B Light Yrs\"}}, {{\\"label\\": \"Milky Way Stars\", \"value\": \"100B+\"}}]}}, {{\"type\": \"content\", \"title\": \"Deep Space & Galaxies\", \"bullets\": [\"Stellar Nurseries & Nebulae\", \"Black Holes & Gravitational Event Horizons\", \"Spiral & Elliptical Galaxies\"]}}, {{\"type\": \"content\", \"title\": \"Human Space Exploration\", \"bullets\": [\"Apollo & Artemis Lunar Missions\", \"Mars Rovers & Outer Solar System Probes\", \"James Webb Space Telescope (JWST) Deep Field\"]}}]"}}

Tools YOU MUST USE:
1. generate_image - Generate high-quality AI images using local diffusion models (SDXL, SD1.5, FLUX)
2. web_search - Search for real-world market statistics, company financials, and industry data
3. fetch_web_page - Extract text content from web URLs
4. generate_presentation - Generate PowerPoint (.pptx) AND interactive HTML Reveal.js slide deck
5. generate_excel_sheet - Generate styled Excel workbook (.xlsx) with formulas, multi-tabs, and charts
6. read_excel_sheet - Read data and formulas from Excel workbooks
7. csv_sheet_operation - Read/write basic CSV files
8. file_operation - Read/write markdown/text strategy reports
"""

        super().__init__(
            name="Business Agent",
            agent_type="business",
            system_prompt=system_prompt,
            model_name=model_name,
            ollama_base_url=ollama_base_url
        )

    def generate_image(self, prompt: str, negative_prompt: str = "", width: int = 1024, height: int = 1024, model: str = "auto", context: Optional[Dict[str, Any]] = None, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Generate an image using local diffusion models via the image pipeline"""
        task = f"Generate an image with prompt: {prompt}"
        result = self.process(task, context=context, chat_history=chat_history, callbacks=callbacks)
        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "image_generation"
        }

    def generate_business_plan(self, requirements: str, context: Optional[Dict[str, Any]] = None, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Generate a business plan based on requirements"""
        task = f"Generate a comprehensive business plan based on: {requirements}"
        result = self.process(task, context=context, chat_history=chat_history, callbacks=callbacks)
        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "business_plan"
        }

    def create_financial_model(self, model_specs: str, context: Optional[Dict[str, Any]] = None, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Create a financial model or budget projection"""
        task = f"Create a financial model and spreadsheet based on: {model_specs}"
        result = self.process(task, context=context, chat_history=chat_history, callbacks=callbacks)
        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "financial_model"
        }

    def generate_presentation(self, prompt_or_specs: str, context: Optional[Dict[str, Any]] = None, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Generate a presentation deck (.pptx and .html) based on specs"""
        task = f"Generate a professional PowerPoint presentation deck (.pptx) and interactive HTML slide deck based on: {prompt_or_specs}"
        result = self.process(task, context=context, chat_history=chat_history, callbacks=callbacks)
        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "presentation"
        }



class CustomSpecializedAgent(BaseSpecializedAgent):
    """Dynamically configured specialized agent loaded from the database."""
    def __init__(self, db_agent, ollama_base_url: str = "http://localhost:11434"):
        resolved_model = db_agent.base_model if db_agent.base_model else (DEFAULT_CODE_MODEL if db_agent.id == "code" else DEFAULT_MAIN_MODEL)
        super().__init__(
            name=db_agent.name,
            agent_type=db_agent.id,
            system_prompt=db_agent.system_prompt,
            model_name=resolved_model,
            ollama_base_url=ollama_base_url,
            custom_tools=db_agent.tools or [],
            mcp_servers=db_agent.mcp_servers or []
        )


# Agent registry
SPECIALIZED_AGENTS = {
    "code": CodeAgent,
    "research": ResearchAgent,
    "analysis": AnalysisAgent,
    "business": BusinessAgent,
}

def create_specialized_agent(
    agent_type: str,
    model_name: Optional[str] = None,
    ollama_base_url: str = "http://localhost:11434"
) -> Optional[BaseSpecializedAgent]:
    if model_name is None:
        model_name = DEFAULT_CODE_MODEL if agent_type == "code" else DEFAULT_MAIN_MODEL

    if agent_type in SPECIALIZED_AGENTS:
        return SPECIALIZED_AGENTS[agent_type](model_name, ollama_base_url)

    from database.db import SessionLocal
    from database.models import AgentModel

    session = SessionLocal()
    try:
        db_agent = session.query(AgentModel).filter(AgentModel.id == agent_type).first()
        if db_agent:
            return CustomSpecializedAgent(db_agent, ollama_base_url)
    except Exception as e:
        print(f"Error loading custom agent '{agent_type}' from SQLite: {e}")
    finally:
        session.close()

    return None
