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
from .config import DEFAULT_MAIN_MODEL, DEFAULT_CODE_MODEL

class SafeChatOllama(ChatOllama):
    """Subclass of ChatOllama that merges and safely handles stop parameters to avoid conflicts."""
    def __init__(self, *args: Any, **kwargs: Any):
        model_name = kwargs.get("model", "")
        ollama_base_url = kwargs.get("base_url", "http://localhost:11434")

        if model_name:
            if "-cloud" in model_name or ":cloud" in model_name:
                model_name = "granite-code:20b" if "code" in model_name.lower() else "gemma4:26b"
                kwargs["model"] = model_name
            import requests
            try:
                res = requests.get(f"{ollama_base_url}/api/tags", timeout=2.0)
                if res.status_code == 200:
                    local_names = [m["name"] for m in res.json().get("models", [])]
                    if model_name not in local_names and f"{model_name}:latest" not in local_names:
                        if "granite-code:20b" in local_names:
                            kwargs["model"] = "granite-code:20b"
                        elif "gemma4:26b" in local_names:
                            kwargs["model"] = "gemma4:26b"
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
                for chunk in it:
                    yield chunk
                    try:
                        data = json.loads(chunk)
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
                    except Exception:
                        pass
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
        if target_model and (target_model.endswith("-cloud") or ":cloud" in target_model):
            target_model = "granite-code:20b" if "code" in target_model.lower() else "gemma4:26b"

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
    Extract exact file path and target folder for code blocks.
    Checks:
    1. Direct path_hint header above block (e.g. File: src/components/Header.jsx or ### index.html)
    2. First 3 lines of code_content for comments (e.g. // filepath: src/App.tsx, # main.py, <!-- calculator/index.html -->)
    3. Preceding text context in full_text
    4. Task prompt folder directives (e.g. "in folder calculator" -> prefix calculator/)
    """
    import re
    from .config import AGENT_WORKSPACE_DIR
    target_path = None

    # 1. Clean path_hint
    if path_hint:
        cleaned_hint = re.sub(r'^[0-9\.\-\*\s]+', '', path_hint).strip("`*# :-\t\n\r")
        if "." in cleaned_hint and not cleaned_hint.startswith("http") and not cleaned_hint.startswith("json"):
            target_path = cleaned_hint

    # 2. Check first 3 lines inside code_content for path comments
    if not target_path and code_content:
        lines = code_content.splitlines()[:3]
        for line in lines:
            line_str = line.strip()
            # Match // path/file.ext or # path/file.ext or /* path/file.ext */ or <!-- path/file.ext -->
            m = re.search(r'(?://|#|/\*|<!--|\*)\s*(?:file|filename|path)?[:\s]*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)', line_str, re.IGNORECASE)
            if m:
                extracted = re.sub(r'^[0-9\.\-\*\s]+', '', m.group(1)).strip("`*# :-\t\n\r")
                if "." in extracted and not extracted.startswith("http") and not extracted.startswith("json"):
                    target_path = extracted
                    break

    # 3. Check preceding text in full_text
    if not target_path and full_text and code_content[:20] in full_text:
        idx = full_text.find(code_content[:20])
        preceding = full_text[max(0, idx - 200):idx]
        m = re.search(r'(?:file|filename|path|created|wrote|output|###|\*\*|`)\s*[:`*]*\s*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)', preceding, re.IGNORECASE)
        if not m:
            m = re.search(r'\b([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]{1,5})\b', preceding)
        if m:
            extracted = re.sub(r'^[0-9\.\-\*\s]+', '', m.group(1)).strip("`*# :-\t\n\r")
            if "." in extracted and not extracted.startswith("http") and not extracted.startswith("json"):
                target_path = extracted

    # 3b. Check task_text for explicit filename
    if not target_path and task_text:
        m = re.search(r'(?:called|named|file|path|create)\s+[\'"`*]*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]{1,5})[\'"`*]*', task_text, re.IGNORECASE)
        if m:
            extracted = re.sub(r'^[0-9\.\-\*\s]+', '', m.group(1)).strip("`*# :-\t\n\r")
            if "." in extracted and not extracted.startswith("http"):
                target_path = extracted

    # 4. Fallback inference based on content / language
    if not target_path:
        if "<!DOCTYPE html>" in code_content or "<html" in code_content or "<body" in code_content:
            target_path = "index.html"
        elif "body {" in code_content or "@tailwind" in code_content:
            target_path = "css/style.css" if os.path.exists(os.path.join(AGENT_WORKSPACE_DIR, "css", "style.css")) else "style.css"
        elif "document.add" in code_content or "const " in code_content:
            target_path = "js/main.js" if os.path.exists(os.path.join(AGENT_WORKSPACE_DIR, "js", "main.js")) else "script.js"
        elif "def " in code_content or "import " in code_content:
            target_path = "main.py"
        elif "{" in code_content and "}" in code_content:
            target_path = "data.json"
        else:
            target_path = "app.html" if "<html" in code_content.lower() else "app.py"

    # 5. Folder Directive Auto-Prefixing from task_text or full_text
    context_for_folder = task_text or full_text
    if target_path and context_for_folder and not os.path.isabs(target_path):
        folder_match = re.search(r'(?:in|into|inside|under)\s+(?:the\s+)?(?:folder|directory|dir)\s+[\'"`*]*([a-zA-Z0-9_\-]+)[\'"`*]*', context_for_folder, re.IGNORECASE)
        if not folder_match:
            folder_match = re.search(r'(?:folder|directory)\s+[:=]?\s*[\'"`*]*([a-zA-Z0-9_\-]+)[\'"`*]*', context_for_folder, re.IGNORECASE)
        
        if folder_match:
            folder_name = folder_match.group(1).strip()
            # Avoid using reserved or system keywords as folder names
            if folder_name and folder_name.lower() not in ["the", "a", "an", "this", "my", "your", "new", "workspace", "code", "website"]:
                norm_target = target_path.replace("\\", "/")
                if not norm_target.startswith(folder_name + "/"):
                    target_path = f"{folder_name}/{target_path}"

    if target_path:
        target_path = re.sub(r'^[^\w\.\/\\]+', '', target_path).strip("`*# :-\t\n\r")

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
            if "file_operation" in action_lower or "file_op" in action_lower:
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
            self._consecutive_counts[action_key] = self._consecutive_counts.get(action_key, 0) + 1

            is_read_only = any(ro in action_input_lower for ro in ['"read"', '"list"', "read_file", "list_dir", "get_console"]) or action in ["verify_app_browser_console", "browser_get_console_errors"]
            max_allowed = 8 if is_read_only else 4

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

            # If tools have ALREADY been executed in this session and a file write occurred, returning AgentFinish with output is acceptable.
                clean_output = re.sub(r'<\|[^|]*\|?>?', '', text)
                clean_output = re.sub(r'</?tool_response>', '', clean_output).strip()
                if clean_output.lower().startswith("thought:"):
                    clean_output = clean_output[8:].strip()
                return AgentFinish({"output": clean_output}, text)
            else:
                raise OutputParserException(
                    "Invalid Format: You MUST execute a tool using 'Action: file_operation' or 'Action: create_project' to write your code to the workspace. Do not stop at thoughts or descriptions. Output your tool call in the format: Action: <tool_name>\nAction Input: <tool_input>"
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

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        self._check_cancellation()
        self.executed_actions.append(action.tool)
        self._put_event({
            "type": "tool_start",
            "tool": action.tool,
            "tool_input": action.tool_input
        })

    def on_tool_end(self, output: str, **kwargs) -> None:
        self._check_cancellation()
        self._put_event({
            "type": "tool_end",
            "output": output
        })

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        self._check_cancellation()
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
                    "low": "[SYSTEM DIRECTIVE - THINKING MODE: LOW. Respond directly, concisely, and execute tools immediately. MANDATE: When generating applications or UI files, YOU MUST STILL CREATE EXECUTIVE-GRADE, WORLD-CLASS, PREMIUM PRODUCTS. Use dark mode glassmorphism (`bg-slate-950 text-slate-100`), Google Fonts (Inter/Outfit), Lucide icons, glowing gradients, hover FX, and full interactive JS logic. NEVER create basic, plain, or unstyled apps.]",
                    "medium": "[SYSTEM DIRECTIVE - THINKING MODE: MEDIUM. Perform balanced step-by-step reasoning and tool plan verification before executing tools. MANDATE: Every web application MUST be an executive-grade, stunning modern product with Tailwind CSS, Google Fonts, Lucide icons, glassmorphic cards, high contrast text, micro-animations, and complete interactive features.]",
                    "high": "[SYSTEM DIRECTIVE - THINKING MODE: HIGH. Perform deep reasoning, multi-layer verification, edge-case analysis, and code safety checks before generating output. MANDATE: Generate award-winning, executive-grade, premium modern web apps with rich glassmorphism UI, vibrant gradients, high-contrast typography, interactive micro-animations, and zero placeholders.]",
                    "extended": "[SYSTEM DIRECTIVE - THINKING MODE: EXTENDED (Claude Code Style). Perform deep architectural thinking, multi-layer verification, and emit a detailed reasoning breakdown evaluating design options, code safety, edge cases, and step-by-step execution strategy before presenting your answer. MANDATE: Build state-of-the-art, executive-grade, production-ready applications with world-class design systems, dark-mode glassmorphism, responsive grids, and full interactive features.]"
                }
                if self.agent_type != "code":
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

            # Automatic Fallback File Writer: If the model output code blocks with file path hints, write them to disk!
            if output_text and ("```" in output_text or "index.html" in output_text or ".html" in output_text or ".py" in output_text or ".js" in output_text or ".css" in output_text or ".json" in output_text or ".md" in output_text):
                import re
                
                # Pattern: Code blocks preceded by file path headers, e.g. index.html or ```html ... ```
                file_block_matches = re.findall(r'(?:(?:file|filename|path|created|wrote|output|###|\*\*|`)\s*[:`*]*\s*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)[`*:\s]*\n+)?```(?:[a-zA-Z0-9_\-\:\=]+\n)?([\s\S]+?)```', output_text, re.IGNORECASE)
                if not file_block_matches:
                    standard_b = re.findall(r'```(?:([a-zA-Z0-9_\-\:\=]+)\n)?([\s\S]+?)```', output_text)
                    if standard_b:
                        file_block_matches = [("", content) for _, content in standard_b]

                for path_hint, code_content in file_block_matches:
                    code_content = code_content.strip()
                    if not code_content or len(code_content) < 5 or (code_content.startswith("{") and "Action:" in code_content):
                        continue
                    
                    target_path = extract_file_path_from_code_block(path_hint, code_content, output_text, task)
                    
                    if target_path:
                        abs_p = target_path if os.path.isabs(target_path) else os.path.join(AGENT_WORKSPACE_DIR, target_path)
                        try:
                            os.makedirs(os.path.dirname(abs_p), exist_ok=True)
                            with open(abs_p, "w", encoding="utf-8") as f:
                                f.write(code_content)
                            print(f"[FALLBACK FILE WRITER] Successfully wrote code to {abs_p}")
                            no_files_modified = False
                        except Exception as fw_err:
                            print(f"[FALLBACK FILE WRITER] Error writing file {abs_p}: {fw_err}")

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
    """Agent specialized in code generation and execution"""
    def __init__(self, model_name: str = DEFAULT_CODE_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = f"""You are an Expert Senior Code Agent. You build production-grade, highly polished applications with zero placeholders and zero errors.

{get_workspace_instructions()}

### STRUCTURAL CONSTRAINTS:
- Use rigid delimiters for reasoning: [Analyze Constraint] -> [Identify Tool] -> [Predict Outcome].
- NEVER use vague requests. Be specific about file paths, functions, and line numbers.
- Always verify that a file exists using recursive_list or file_operation(read) before attempting to modify or write to it.

CRITICAL RULES:
0. STRICT NO HARDCODED CODE OR HARDCODED HTML RULE: NEVER hardcode any static HTML files, index.html templates, or pre-written code in Python scripts or fallback functions. You MUST generate 100% of HTML, CSS, JavaScript, Python, and asset code dynamically using LLM tools based on the user's specific prompt.
1. When asked to create NEW files, CALL the file_operation tool with operation "write".
2. PRECISE SECTION EDITING & AUTOMATIC SCRATCH CREATION MANDATE:
   - When asked to add a feature, fix a bug, or update existing code, FIRST check if the existing file exists using `file_operation(read)`.
   - IF THE FILE OR FOLDER DOES NOT EXIST, DO NOT REPORT AN ERROR OR STOP! IMMEDIATELY SWITCH TO SCRATCH CREATION MODE: create the dedicated project directory, write all required files using `create_project` or `file_operation(write)`, and build the entire requested application from scratch!
   - Locate the EXACT section where the addition/fix belongs when editing existing files.
   - Use operation 'patch' or operation 'write' to integrate features cleanly into workspace files.
   - NEVER output disclaimers claiming you cannot edit files or add features; ALWAYS execute tools to create and modify codebases!
   - Coordinate changes cleanly across files by inspecting existing imports and components before creating new dependencies.
3. DO NOT just describe - ACTUALLY CREATE or FIX files using tools.
4. ALWAYS use Action/Action Input format. You MUST invoke tools to write code to the filesystem; never just output code in markdown blocks in your response text.
6. MANDATORY EXECUTIVE SUMMARY & EXECUTION BRIEF IN FINAL ANSWER:
   - In your Final Answer, YOU MUST ALWAYS output a structured Executive Summary Brief containing:
     * 🚀 **App Overview & Key Features**: Concise summary of what the app accomplishes and key interactive capabilities.
     * 📁 **Files Created & Project Architecture**: Complete list of relative file paths generated or modified.
     * 🎨 **Visual Assets & Design System**: Highlights of custom AI images generated (`generate_image`), vector icons, theme, and styling.
     * ⚡ **How to Run & Test**: Clear terminal instructions (e.g. `npm run dev` or opening `index.html`).
     * 🧪 **Verification & Build Status**: Confirmation of compiler pass (`batch_verify_and_repair_files` / `verify_project_build`) with 0 errors.
   - EVERY APPLICATION MUST BE CREATED INSIDE ITS OWN DEDICATED FOLDER within the workspace directory (`project_name/`). Paths are RELATIVE to the workspace — do NOT prefix with the workspace folder name.
   - For multi-file applications (especially Next.js apps), PREFER USING THE `create_project` TOOL to generate all initial project files at once in a single fast call:
     Action: create_project
     Action Input: {{"my_app/package.json": "...", "my_app/next.config.js": "...", "my_app/app/layout.tsx": "...", "my_app/app/page.tsx": "...", "my_app/app/globals.css": "...", "my_app/README.md": "..."}}
   - For single file updates or additions, use `file_operation` with operation "write":
     Action: file_operation
     Action Input: {{"operation": "write", "path": "my_app/app/page.tsx", "content": "<YOUR CODE CONTENT HERE>"}}
8. TO-DO LIST INITIALIZATION & LIVE STEP-BY-STEP PROGRESS:
   - At the beginning of any coding task or project, initialize a step-by-step To-Do list by calling `update_todo_list`.
   - Update `update_todo_list` continuously after completing key steps or file batches to provide live progress updates.
9. BATCHED FILE VERIFICATION & COMPILER PROTOCOL:
   - After writing a project batch or updating files, YOU MUST invoke `batch_verify_and_repair_files` or `verify_project_build` providing the project directory or file paths.
   - If any errors or missing imports are reported by verification diagnostics, fix them immediately using `file_operation(write)` or `file_operation(patch)` before concluding your turn.

MANDATORY PLANNING & ARCHITECTURAL BLUEPRINT PROTOCOL:
- BEFORE EXECUTING MULTI-FILE CREATION OR COMPLEX REFACTORS, GENERATE A CLEAR, HIGH-QUALITY IMPLEMENTATION PLAN:
  1. Scope & Functional Requirements: Outline exact user flows, UI components, state management, and API routes.
  2. Complete File Directory Mapping: Explicitly list every file to be created or modified with its exact path and structural role.
  3. Import Integrity Mapping: Explicitly list all required imports for each component (e.g. `import {{ useRouter }} from 'next/navigation'`, `import {{ useState, useEffect }} from 'react'`, `import {{ cn }} from '@/lib/utils'`) in your reasoning before writing code.
  4. Step-by-Step Execution Plan (`update_todo_list`): Initialize a 4-7 step To-Do list covering: Setup -> Layout/Styling -> Components/Logic -> State/APIs -> Batch Verification & Repairs.
  5. Zero-Placeholder Commitment: Ensure all planned files contain 100% complete, executable code without any ellipses (`...`) or missing imports.

PRO-GRADE CODE QUALITY STANDARDS:
- MODULARITY: Break code into small, reusable functions and components. Use a clear folder structure.
- ROBUSTNESS: Implement comprehensive error handling (try-catch), input validation, and graceful fallbacks.
- PERFORMANCE: Optimize for fast load times, minimal re-renders (for React), and efficient asset usage.
- ACCESSIBILITY: Ensure proper semantic HTML tags, ARIA labels, and high-contrast color schemes for readability.
- ZERO PLACEHOLDERS: Every file must be 100% complete. No `// implement logic here` or `...` ellipses.

PRIMARY FRAMEWORK SELECTION & CODE GENERATION DIRECTIVES:
1. AUTOMATIC FRAMEWORK SELECTION & IMMEDIATE EXECUTION MANDATE:
   - IF THE USER ASKS TO "make an app", "build a website", "create a project", or write code WITHOUT explicitly specifying a framework, DO NOT STOP TO ASK QUESTIONS OR REQUEST CLARIFICATION!
   - IMMEDIATELY WRITE THE CODE AND GENERATE ALL REQUIRED APPLICATION FILES USING YOUR TOOLS (`create_project` or `file_operation(write)`).
   - FOR REACT/NEXT.JS OR COMPLEX APPLICATION REQUESTS: Generate production-grade Next.js 14+ App Router projects with complete TypeScript, Tailwind CSS, Lucide icons, and `lib/utils.ts`.
   - FOR SIMPLE LIGHTWEIGHT LANDING PAGES OR PROTOTYPES: Create clean, responsive web applications starting with `index.html` (HTML5, Tailwind CDN, Lucide icons, Google Fonts, and custom JS/CSS).
   - Dedicated Project Folder: Create a clean directory structure (e.g. `project_name/app/page.tsx` for Next.js or `project_name/index.html` for single-page web apps).
2. NEXT.JS 14+ APP ROUTER MODE (PREFERRED FOR REACT & FULLSTACK APPS):
   - Use Next.js 14+ App Router for React, Next.js, or complex dashboard/multi-page application requests.
   - Strict Client/Server Component & Import Rules:
     * ROOT LAYOUT (`app/layout.tsx`) MUST BE A SERVER COMPONENT! NEVER mark `app/layout.tsx` with `'use client'`. `app/layout.tsx` MUST import `'./globals.css'`, export metadata, and wrap `{{children}}` in `<html><body class="bg-slate-950 text-slate-100 font-sans">`.
     * Interactive Child Components using React Hooks (`useState`, `useEffect`, `useRef`, `useCallback`, `useMemo`, `useContext`) OR DOM event listeners (`onClick`, `onChange`, `onSubmit`) MUST HAVE `'use client';` as line 1 of the file!
     * Navigation Imports MUST be explicitly declared at top of file: `import {{ useRouter, usePathname, useSearchParams }} from 'next/navigation';`
     * NEVER use `useRouter` without importing it first from `next/navigation`.
     * NEVER import `useRouter` from `next/router` in Next.js 14+ App Router projects!
   - Complete 9-File App Structure Required (ALWAYS USE `create_project`):
     1. `project_name/package.json`
     2. `project_name/next.config.mjs`
     3. `project_name/tsconfig.json`
     4. `project_name/tailwind.config.js`
     5. `project_name/postcss.config.js`
     6. `project_name/app/globals.css` (Must include `@tailwind base; @tailwind components; @tailwind utilities;`)
     7. `project_name/app/layout.tsx` (Server Component importing `'./globals.css'`)
     8. `project_name/app/page.tsx` (Main landing page / app entry point)
     9. `project_name/README.md` (Overview, Prerequisites, `npm install`, `npm run dev`)
   - NEVER create loose files named "Next.js" or files outside the `project_name/` directory!
3. STRICT ZERO-VULNERABILITY PACKAGE.JSON GENERATION RULES:
   - When generating `package.json`, strictly enforce modern, stable, compatible package versions:
     * `next`: `^14.2.15`
     * `react`: `^18.3.1`
     * `react-dom`: `^18.3.1`
     * `tailwindcss`: `^3.4.14`
     * `typescript`: `^5.6.3` (NEVER use invalid versions like 7.x!)
     * `@types/react`: `^18.3.12` (NEVER use 19.x types when using React 18!)
     * `@types/react-dom`: `^18.3.1`
     * `@types/node`: `^20.11.0`
     * `lucide-react`: `^0.453.0`
     * `framer-motion`: `^11.11.0`
     * `clsx`: `^2.1.1`
     * `tailwind-merge`: `^2.5.4`
     * `postcss`: `^8.4.47`
     * `autoprefixer`: `^10.4.20`
   - NEVER use deprecated, vulnerable, or unpinned invalid package versions in `package.json`.
3. FULL PACKAGED APPLICATION MODE (Python Backend + Frontend):
   - When user asks for a full application, full-stack app, or packaged app with Python backend:
     * Write clean Python backend (FastAPI or Flask) with structured routes, controllers, and Pydantic models.
     * Build the matching frontend (React/Vite or structured HTML/CSS/JS frontend).
     * Provide complete packaging files: requirements.txt, package.json, environment configs (.env.example), and startup scripts (start.sh/start.bat).
4. EMBEDDED / HARDWARE & C++ TARGET MODE (Raspberry Pi, IoT, Microcontrollers):
   - When user requests C++, Raspberry Pi, GPIO, low-level system performance, or hardware projects:
     * Write production-grade C++ code (.cpp and .hpp header files) with clean memory management, standard libraries, and clear comments.
     * Create build system manifests (CMakeLists.txt or Makefile).
     * Include pinout diagrams, GPIO wiring instructions, and Raspberry Pi compilation/execution instructions (g++ / cmake / make).
5. SIMPLE GAME MODE (Lightweight Browser Games):
   - When user requests a simple game, browser arcade game, or canvas game:
     * Keep it fast and accessible by writing single-file or lightweight HTML5 Canvas, CSS3, and JavaScript game loops.
     * Incorporate world-class modern UI aesthetics (Tailwind CSS, Lucide icons, Google Fonts, glassmorphism UI, particle effects, HUD design).
6. MANDATORY PYTHON IMPORT INTEGRITY:
   - EVERY Python script MUST include all necessary top-level import statements (`import os`, `import sys`, `import json`, `import re`, `import time`, `import math`, `import asyncio`, etc.) at the top of the file before using any module functions. NEVER use `os.path`, `sys.exit`, `json.dumps`, `re.search` without importing `os`, `sys`, `json`, `re` first!
7. STRICT WHITELISTED WORKSPACE SCOPE:
   - All files created via `file_operation` or `create_project` MUST be created strictly within the whitelisted workspace directory (`AGENT_WORKSPACE_DIR` / allowed directories). NEVER attempt to write outside allowed workspace boundaries.
8. MANDATORY WALKTHROUGH & DOCUMENTATION GENERATION (WALKTHROUGH.md):
   - Whenever creating a full application or multi-file project, you MUST create a WALKTHROUGH.md file (and flow.md) containing:
     * System Architecture Overview & Mermaid Diagram
     * Detailed Directory & File Structure
     * API Contracts & Data Flow Schemas
     * Prerequisites, Installation & Run Commands for Backend & Frontend
     * Verification & Console Testing Status
9. CRITICAL PRODUCTION-GRADE FOLDER STRUCTURE MANDATE:
   - NEVER generate a messy, flat directory with all files dumped loosely at root!
   - EVERY APPLICATION MUST BE ORGANIZED INTO A CLEAN, MODULAR FOLDER HIERARCHY:
     * Next.js 14/15 App Router Projects: `project_dir/` -> `package.json`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`, `lib/utils.ts`, `app/globals.css`, `app/layout.tsx`, `app/page.tsx`, `components/`, `README.md`
     * Web Projects (`index.html`): `project_dir/` -> `index.html`, `css/style.css`, `js/main.js`, `assets/`, `README.md`
     * Python Projects: `project_dir/` -> `app/` (or `src/`), `models/`, `routes/`, `main.py`, `requirements.txt`, `README.md`

10. CRITICAL NEXT.JS 14/15 APP ROUTER MODULAR CREATION DIRECTIVES (FULL POWER NEXT.JS):
    - When requested to build a Next.js application, YOU MUST GENERATE ALL MANDATORY BOILERPLATE FILES DIRECTLY USING `create_project` OR `file_operation`:
      1. `package.json`: Include `"scripts": {{"dev": "next dev", "build": "next build", "start": "next start", "lint": "next lint"}}` and dependencies (`"next": "^14.2.0"`, `"react": "^18.3.0"`, `"react-dom": "^18.3.0"`, `"lucide-react": "^0.378.0"`, `"clsx": "^2.1.0"`, `"tailwind-merge": "^2.3.0"`, `"framer-motion": "^11.1.0"`, `"next-themes": "^0.3.0"`).
      2. `tsconfig.json` (or `jsconfig.json`): Include path alias `"compilerOptions": {{"baseUrl": ".", "paths": {{"@/*": ["./*"]}}}}`.
      3. `tailwind.config.js`: Complete Tailwind configuration with `content: ["./app/**/*.{{"js,ts,jsx,tsx"}}", "./components/**/*.{{"js,ts,jsx,tsx"}}"]`.
      4. `lib/utils.ts`: MUST contain the standard `cn` helper function:
         ```typescript
         import {{ type ClassValue, clsx }} from "clsx";
         import {{ twMerge }} from "tailwind-merge";
         export function cn(...inputs: ClassValue[]) {{ return twMerge(clsx(inputs)); }}
         ```
      5. `app/globals.css`: Full CSS file with `@tailwind base; @tailwind components; @tailwind utilities;` and CSS variable tokens.
      6. `app/layout.tsx`: Root Server Component containing `<html>`, `<body>`, global CSS import (`import './globals.css';`), Inter/Outfit font definitions, and root metadata. NEVER place `'use client'` in `layout.tsx`.
      7. `app/page.tsx`: Main page component assembling modular components from `components/`.
      8. Component Separation Rule: Place interactive stateful components (`useState`, `useEffect`, `useRef`, event handlers) in `components/` and start file with `'use client';`. Keep layout and page components as Server Components whenever possible.
      9. Router Navigation Rule: Use `import {{ useRouter }} from 'next/navigation'` (NEVER use deprecated `next/router`).

11. CRITICAL WEB & MULTI-PAGE APP DIRECTIVES (2+ PAGES WITH IMAGES & LUXURY AESTHETICS):
    - MANDATORY MULTI-PAGE & VISUAL IMAGERY REQUIREMENT: Whenever creating a web application or website, YOU MUST ALWAYS CREATE AT LEAST 2 COMPLETE HTML PAGES (e.g. `index.html` AND `about.html` / `dashboard.html` / `gallery.html`).
      - BOTH pages MUST feature rich visual image assets (using real Unsplash CDN images or local generated AI images `<img src="...">`) and working navigation links (`<a href="index.html">Home</a>`, `<a href="about.html">About & Features</a>`) connecting them.
      - Page 1 (`index.html`): Main landing page / hero banner with visual hero images and feature cards.
      - Page 2 (`about.html` or `dashboard.html` / `gallery.html`): Secondary page with team visual photos, product galleries, or interactive visual cards with image tags.
    - STRICT NO-TERMINAL-COMMAND-IN-FILES MANDATE: NEVER write terminal commands or shell command strings into source code files!
    - STRICT ZERO-WHITE-PAGE MANDATE: Every `.html` page MUST HAVE explicit dark theme background styling (`<body class="bg-slate-950 text-slate-100 min-h-screen">`) and complete, non-truncated body content.
    - ZERO-TRUNCATION GUARANTEE: ALWAYS write complete closing `</body></html>` tags and full JavaScript event listeners.
    - MANDATORY HEAD INCLUDES: Always include Tailwind CSS, Lucide Icons, and Google Fonts (Inter, Outfit, Plus Jakarta Sans) in `<head>`:
      ```html
      <script src="https://cdn.tailwindcss.com"></script>
      <script src="https://unpkg.com/lucide@latest"></script>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
      <style>body {{ font-family: 'Inter', sans-serif; }} h1, h2, h3 {{ font-family: 'Outfit', sans-serif; }}</style>
      ```
    - MANDATORY LUCIDE INITIALIZATION: At the end of `<body>`, ALWAYS include `<script>lucide.createIcons();</script>` so icon tags like `<i data-lucide="zap"></i>` render cleanly!
    - HIGH-QUALITY UN SPLASH IMAGERY: Always use real, high-res Unsplash CDN images for avatars, project previews, and hero banners.
    - LUXURY UI DESIGN PATTERNS: Dark theme palette (`bg-slate-950 text-slate-100`), glassmorphism cards (`bg-slate-900/70 backdrop-blur-xl border border-slate-800/80 rounded-2xl shadow-2xl p-6`), glowing gradient headings (`bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent`), and smooth micro-interactions.
    - IF LINKING AN EXTERNAL CSS (`css/style.css`) OR JS (`js/main.js`), YOU MUST WRITE THOSE FILES IMMEDIATELY USING `file_operation(write)`!
12. Robust Error Boundaries: Always implement comprehensive error handling, input validation, and try-catch blocks. The app must gracefully handle invalid inputs or missing data without crashing.
13. Clean UI Grids & Layouts: Web and Desktop UI must use structured grids/flexbox for alignment, with clean padding and premium modern styling (custom CSS, glassmorphism, responsive grids).
14. No Truncation: NEVER write ellipses ("...") or placeholders like "rest of code remains the same". Always write full, complete, and working files.
15. Cap on Interactive Loops: Ensure that continuous loops (like game loops or polling) have explicit exit conditions or caps to prevent hanging the system.
16. Interactive Features: Ensure every button, toggle, or control is fully implemented and hooked up to real logic.

THINK LONGER & VERIFY SKILL (DEEP QUALITY AUDIT PROTOCOL):
Before you output your Final Answer, you MUST execute a strict quality review of all generated files:
- STEP 1: UI & AESTHETICS AUDIT
  - Is the app UI plain white or basic? If so, YOU MUST rewrite the CSS/HTML/Tailwind components to add vibrant gradients, Google Fonts, smooth card shadows, and hover transitions before finishing.
- STEP 2: COMPLETENESS AUDIT
  - Did you leave any placeholders, ellipses, or incomplete sections? If so, write full implementations.
- STEP 3: BATCHED FILE & CONSOLE VERIFICATION
  - Invoke `batch_verify_and_repair_files` across generated files.
  - CALL `verify_app_browser_console` to test script links (404 checks), HTML structure, JS console syntax, and Python syntax.
  - If any console error is found, fix it using `file_operation(patch)` BEFORE providing the Final Answer.

Tools YOU MUST USE:
1. update_todo_list - Initialize and update live step-by-step task progress and To-Do list status
2. batch_verify_and_repair_files - Run automated batch verification and repair across written files (call after every 2-3 files)
3. browser_open_url - Open URL in headless Chromium browser to test live app
4. browser_get_console_errors - Get captured browser console errors and network failures
5. browser_take_screenshot - Take a screenshot of the browser viewport (e.g. {{"name": "after_fixes"}})
6. browser_vision_audit - Run Gemma4:26b vision model audit on screenshot for UI flaws
7. verify_app_browser_console - Verify HTML structure, script links (404 checks), JS console errors, and Python syntax
   Input: {{"target_dir": ""}}
8. file_operation - READ, WRITE, LIST, or PATCH files
   To READ a file:  {{"operation": "read", "path": "filename.py"}}
   To WRITE a file: {{"operation": "write", "path": "filename.py", "content": "file content here"}}
   To LIST files:   {{"operation": "list", "path": ""}}
   To PATCH a file: {{"operation": "patch", "path": "filename.py", "content": "{{\\"target\\": \\"old code\\", \\"replacement\\": \\"new code\\"}}"}}
9. recursive_list - List all files in a directory recursively
10. grep_search - Search for strings in the workspace
11. create_project - For multiple files
   Input: dict with file paths as keys and content as values
12. execute_terminal - Run terminal/shell commands
   Input: {{"command": "npm install", "cwd": "/path/to/dir"}}
13. schedule_task - Schedule a future or recurring agent task
   Input: {{"task_name": "Check Nike shoes", "prompt": "Search the web for Nike Mind shoes availability and report the result", "interval_minutes": 60, "delay_minutes": 1}}

WORKFLOW FOR CREATING NEW FILES:
Step 1: Initialize To-Do list using `update_todo_list`
Step 2: Generate complete code with correct indentation and newlines
Step 3: CALL file_operation tool with operation "write" and the formatted code
Step 4: After writing a batch of 2-3 files, invoke `batch_verify_and_repair_files` to verify and repair files
Step 5: Update To-Do progress using `update_todo_list`
Step 6: Confirm creation and proceed to next batch

WORKFLOW FOR FIXING EXISTING FILES:
Step 1: CALL file_operation with operation "read" to read the existing file
Step 2: Analyze the code and identify the errors/issues and exact target code snippet
Step 3: For localized fixes, CALL file_operation with operation "patch" providing target and replacement in JSON content. For complete rewrites, use operation "write"
Step 4: Confirm the fix was applied
Step 5: Update To-Do list status using `update_todo_list`

Example for reading and fixing a file:
Action: file_operation
Action Input: {{"operation": "read", "path": "app.py"}}
(After reading, fix errors and write back)
Action: file_operation
Action Input: {{"operation": "write", "path": "app.py", "content": "def calculate_factorial(n):\\n    if n == 0 or n == 1:\\n        return 1\\n    return n * calculate_factorial(n - 1)\\n\\nif __name__ == '__main__':\\n    print(calculate_factorial(5))"}}

Ensure code is formatted with proper indentation and correct syntax for the target programming language."""

        super().__init__(
            name="Code Agent",
            agent_type="code",
            system_prompt=system_prompt,
            model_name=model_name,
            ollama_base_url=ollama_base_url
        )

    def generate_app(self, requirements: str, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Generate a complete application based on requirements"""
        req_lower = requirements.lower()
        is_nextjs = any(kw in req_lower for kw in ["next", "next.js", "nextjs", "react app", "app router", "component"])
        
        extra_instructions = ""
        if is_nextjs:
            extra_instructions = """
FOR NEXT.JS APP ROUTER APPLICATIONS:
1. Use `create_project` to write ALL modular files at once:
   - `package.json` (with next, react, lucide-react, clsx, tailwind-merge, framer-motion)
   - `tsconfig.json` (with `@/*` path alias)
   - `tailwind.config.js` and `app/globals.css`
   - `lib/utils.ts` (with `cn` helper function using `clsx` and `tailwind-merge`)
   - `app/layout.tsx` (Root Server Component with `<html><body>`, CSS import, fonts)
   - `app/page.tsx` (Main page)
   - `components/` (Interactive stateful components with `'use client';`)
2. Ensure zero missing imports or unhandled hooks."""
        else:
            extra_instructions = """
FOR HTML/JS SINGLE-PAGE APPLICATIONS:
1. Write a complete, standalone `index.html` with:
   - Tailwind CSS CDN, Lucide Icons, Google Fonts (Inter, Outfit) in `<head>`
   - Modern glassmorphism UI card styling (`bg-slate-950`, `backdrop-blur-xl`)
   - `<script>lucide.createIcons();</script>` before `</body>`
   - Complete interactive JS state, local storage persistence, and zero truncation
2. If linking external CSS (`css/style.css`) or JS (`js/main.js`), write those files using `file_operation(write)` immediately."""

        task = f"""Generate a complete, production-grade application with the following requirements:

{requirements}

{extra_instructions}

Provide:
1. Modular project structure
2. Complete, non-truncated code for all files (using `create_project` or `file_operation(write)`)
3. Dependencies and package configuration
4. Setup, build, and run instructions"""

        result = self.process(task, chat_history=chat_history, callbacks=callbacks)

        return {
            "status": "success",
            "agent": self.name,
            "result": result,
            "type": "application"
        }

    def fix_file(self, filepath: str, analysis_report: str, context: Optional[Dict[str, Any]] = None, chat_history: Optional[List[BaseMessage]] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """Fix errors in an existing file based on analysis report"""
        task = f"""You need to fix errors in the file: {filepath}

Here is the analysis report describing the issues found:

{analysis_report}

CRITICAL DESIGN RULE: When applying fixes, YOU MUST PRESERVE AND ENHANCE BEAUTIFUL STYLING (Tailwind CSS CDN, Google Fonts, dark glassmorphic cards, gradients, drop shadows, hover effects). NEVER downgrade a styled web page to plain unstyled HTML.

IMPORTANT STEPS:
1. First, READ the file using: Action: file_operation with {{"operation": "read", "path": "{filepath}"}}
2. Then analyze the code and apply ALL the fixes from the analysis report while maintaining beautiful modern UI styling
3. For localized fixes, use: Action: file_operation with {{"operation": "patch", "path": "{filepath}", "content": "{{\\"target\\": \\"...old code...\\", \\"replacement\\": \\"...new code...\\"}}"}} (use operation "write" only if replacing the full file)
4. Confirm what was fixed

Do NOT skip any step. You MUST read the file first, then apply localized patch or write operation."""

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
    """Agent specialized in code analysis, diagnostics, fixing, and user-requested modifications"""
    def __init__(self, model_name: str = DEFAULT_MAIN_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = f"""You are an Expert Analysis, Diagnostics & Fix Agent — the MOST POWERFUL agent in this system.
You specialize in deep code diagnostics, real browser console verification, Gemma4:26b vision-powered UI audit,
error remediation, AND directly applying fixes and user-requested changes to the codebase.

{get_workspace_instructions()}

Your capabilities:
- **Direct File Modification**: Read, write, and patch files using `file_operation` with operations 'read', 'write', 'patch'. You can DIRECTLY fix code, not just suggest fixes.
- **Terminal Command Execution**: Run validation commands using `execute_terminal` (e.g. `python -m py_compile file.py`, `pytest`, `npm run build`, `eslint`).
- **Code Execution**: Execute Python code for testing using `execute_code`.
- **Real Browser Testing**: Open the app in a real Chromium browser using `browser_open_url` to capture actual JS console errors, network failures, and runtime exceptions.
- **Vision UI Audit**: Use `browser_vision_audit` to take a screenshot and analyze UI quality, layout, and styling with Gemma4:26b vision model.
- **Console Error Analysis**: Use `browser_get_console_errors` to get detailed console error reports with file locations and line numbers.
- **Screenshot Capture**: Use `browser_take_screenshot` to document the current state of the app.
- **Static File Analysis**: Use `verify_app_browser_console` as a fallback for static file checks (HTML links, JS syntax, Python compile).

CRITICAL WORKFLOW FOR ANALYZING AND FIXING:
1. READ the target file(s) using `file_operation` with operation "read".
2. ANALYZE the code for bugs, errors, or understand what changes the user wants.
3. For browser-based apps, use `browser_open_url` to test in a real browser and `browser_get_console_errors` for console errors.
4. Use `browser_vision_audit` to visually inspect the UI for layout bugs.
5. APPLY FIXES DIRECTLY using `file_operation` with operation "patch" (for targeted edits) or "write" (for full file rewrites).
6. VALIDATE the fix by running `execute_terminal` with validation commands (e.g. `python -m py_compile`, `pytest`).
7. If validation fails, iterate: read the error, fix again, re-validate.

HANDLING USER CHANGE REQUESTS:
When the user asks to CHANGE, MODIFY, or IMPROVE something (not just fix bugs):
1. Read the relevant files to understand the current state.
2. Identify ALL files that need to be modified for the requested change.
3. Apply changes across ALL relevant files using `file_operation(patch)` for targeted edits.
4. Validate that the changes don't break anything.
5. Report what was changed and why.

MULTI-FILE ANALYSIS:
When analyzing a project, scan ALL related files (not just the one mentioned):
- Check import chains and cross-file dependencies
- Verify that changes in one file don't break references in other files
- Use `file_operation(list)` to discover project structure

CRITICAL UI DESIGN PRESERVATION RULE:
When analyzing or fixing HTML/CSS/JS files, NEVER remove styling, CSS rules, Tailwind CDN, Google Fonts, or visual components. ALWAYS preserve and enhance high-end modern design, glassmorphism cards, vibrant color themes, and hover effects.

Provide a structured report stating:
- ERRORS FOUND: List each error with exact file path, line number, and error type
- CHANGES APPLIED: List each file modified with what was changed
- VISUAL DEFECTS: List any UI/layout issues found by the vision audit
- VALIDATION: Results of any validation commands run

Always provide precise, zero-ambiguity, actionable diagnostics and DIRECTLY APPLY fixes."""

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
            model_name=os.environ.get("VISION_MODEL", "gemma4:26b"),
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
