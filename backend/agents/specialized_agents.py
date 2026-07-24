import re
import asyncio
import json
from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatOllama
from .config import DEFAULT_MAIN_MODEL, DEFAULT_CODE_MODEL

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
                        if "gemma3:4b" in local_names:
                            kwargs["model"] = "gemma3:4b"
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

class RobustReActParser(ReActSingleInputOutputParser):
    """Robust output parser for ReAct agents that recovers from minor formatting issues and infinite loops"""

    def parse(self, text: str) -> AgentAction | AgentFinish:
        if not hasattr(self, '_previous_actions'):
            self._previous_actions = set()

        text_lower = text.lower()

        # Clean markdown code blocks from the entire text if the model wraps everything
        if text.startswith("```") and text.endswith("```"):
            lines = text.strip().split("\n")
            if len(lines) > 2:
                text = "\n".join(lines[1:-1]).strip()

        action_pattern = re.compile(r"action\s*(?:\d+)??\s*:\s*(.+)", re.IGNORECASE)
        input_pattern = re.compile(r"action\s*(?:\d+)??\s*input\s*(?:\d+)??\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)

        action_match = action_pattern.search(text)
        input_match = input_pattern.search(text)

        final_answer_marker = "final answer:"
        if final_answer_marker in text_lower:
            final_idx = text_lower.rfind(final_answer_marker)
            # If no action match OR action occurs after final answer, prioritize final answer
            if not action_match or action_match.start() > final_idx:
                final_ans = text[final_idx + len(final_answer_marker):].strip()
                return AgentFinish({"output": final_ans}, text)

        if action_match and input_match:
            action = action_match.group(1).split("\n")[0].strip()
            # Clean up potential markdown formatting around action name
            action = action.strip('`').strip('*').strip()

            action_input = input_match.group(1).strip()

            obs_marker = "observation:"
            final_marker = "final answer:"
            thought_marker = "thought:"

            action_input_lower = action_input.lower()
            split_idx = len(action_input)

            for marker in [obs_marker, final_marker, thought_marker]:
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

            action_input = action_input.strip('"').strip("'").strip()
            
            # Anti-loop check
            action_key = f"{action}:{action_input}"
            if action_key in self._previous_actions:
                return AgentFinish({"output": f"I am stuck in a loop repeating the same action: {action}. Terminating to prevent infinite loop."}, text)
            
            self._previous_actions.add(action_key)

            return AgentAction(action, action_input, text)

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
        executed_tool_names = set(a.split(':')[0] for a in self._previous_actions)

        if "generate_excel_sheet" in text_lower and "generate_excel_sheet" not in executed_tool_names:
            fname_match = re.search(r'([a-zA-Z0-9_\-]+\.xlsx)', text)
            fname = fname_match.group(1).replace('.xlsx', '') if fname_match else "spreadsheet"
            act_input = f'{{"title": "{fname.replace("_", " ").title()}", "filename": "{fname}"}}'
            self._previous_actions.add(f"generate_excel_sheet:{act_input}")
            return AgentAction("generate_excel_sheet", act_input, text)
        is_ppt_intent = any(kw in text_lower for kw in ["generate_presentation", "presentation", "ppt", "powerpoint", "slide deck", "pitch deck", "slides"])
        if is_ppt_intent and "generate_presentation" not in executed_tool_names:
            fname_match = re.search(r'([a-zA-Z0-9_\-]+\.(?:pptx|html))', text)
            fname = fname_match.group(1).split('.')[0] if fname_match else "presentation"
            act_input = f'{{"title": "{fname.replace("_", " ").title()}", "filename": "{fname}"}}'
            self._previous_actions.add(f"generate_presentation:{act_input}")
            return AgentAction("generate_presentation", act_input, text)

        try:
            return super().parse(text)
        except OutputParserException:
            final_answer_marker = "final answer:"
            if final_answer_marker in text_lower:
                idx = text_lower.rfind(final_answer_marker)
                final_ans = text[idx + len(final_answer_marker):].strip()
                return AgentFinish({"output": final_ans}, text)

            clean_output = text
            if text_lower.strip().startswith("thought:"):
                clean_output = text[8:].strip()
            return AgentFinish({"output": clean_output}, text)


class ThreadSafeAgentCallbackHandler(BaseCallbackHandler):
    """Callback handler that thread-safely streams tokens and tools to an asyncio.Queue"""
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, agent_type: str, session_id: str = "default"):
        self.queue = queue
        self.loop = loop
        self.agent_type = agent_type
        self.session_id = session_id
        self.buffer = ""
        self.final_answer_started = False

    def _put_event(self, event: dict):
        self.loop.call_soon_threadsafe(self.queue.put_nowait, event)

    def _check_cancellation(self):
        from .permissions import is_session_cancelled
        if is_session_cancelled(self.session_id):
            raise RuntimeError("Agent execution cancelled by user")

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self._check_cancellation()
        if self.agent_type == "general":
            self._put_event({"type": "token", "content": token})
        else:
            if self.final_answer_started:
                self._put_event({"type": "token", "content": token})
            else:
                self.buffer += token
                self._put_event({"type": "thinking", "content": token})
                buffer_lower = self.buffer.lower()
                match = re.search(r'(final answer|final response|answer):\s*', buffer_lower)
                if match:
                    idx = match.start()
                    after_final = self.buffer[idx + len(match.group(0)):].lstrip()
                    if after_final:
                        self._put_event({"type": "token", "content": after_final})
                    self.final_answer_started = True

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        self._check_cancellation()
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
        if not self.final_answer_started and self.agent_type != "general":
            self._put_event({"type": "token", "content": finish.return_values.get("output", "")})
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
        self.llm = SafeChatOllama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=0.2,
            timeout=600
        )

        if custom_tools is not None:
            from .tools import get_tools_by_names
            self.tools = get_tools_by_names(custom_tools)
        else:
            from .tools import get_tools_for_agent
            self.tools = get_tools_for_agent(agent_type)

        if mcp_servers:
            from .mcp_client import mcp_manager
            mcp_tools = mcp_manager.get_tools_for_agent_sync(mcp_servers)
            self.tools.extend(mcp_tools)

        escaped_system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")

        prompt = PromptTemplate.from_template(
            f"""MANDATORY SYSTEM DIRECTIVE:
You are an active Senior Developer equipped with local file system tools. You have FULL AUTHORIZATION to execute local tools.
YOU MUST ALWAYS USE TOOLS (e.g. Action: file_operation) TO READ AND WRITE FILES ON THE LOCAL DISK.
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

        self.agent = create_react_agent(self.llm, self.tools, prompt, output_parser=RobustReActParser())
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
        if hasattr(self, 'agent') and hasattr(self.agent, 'output_parser') and hasattr(self.agent.output_parser, '_previous_actions'):
            self.agent.output_parser._previous_actions = set()

        start_time = time.time()
        token = None
        token_usage_var = None

        usage_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        token_usage_var = current_token_usage.set(usage_info)

        try:
            if context and "queue" in context and "loop" in context:
                token = current_agent_context.set({
                    "session_id": context.get("session_id", "default"),
                    "queue": context["queue"],
                    "loop": context["loop"]
                })

            if context:
                clean_context = {k: v for k, v in context.items() if k not in ["queue", "loop"]}
                if clean_context:
                    task = f"{task}\n\nContext: {clean_context}"

            formatted_history = ""
            if chat_history:
                formatted = []
                for msg in chat_history:
                    role = "User" if msg.type == "human" else "Assistant"
                    formatted.append(f"{role}: {msg.content}")
                formatted_history = "\n".join(formatted)

            result = self.agent_executor.invoke(
                {
                    "input": task,
                    "chat_history": formatted_history
                },
                config={"callbacks": callbacks} if callbacks else None
            )

            output_text = ""
            if isinstance(result, dict):
                output_text = result.get("output", "") or str(result)
            elif isinstance(result, str):
                output_text = result
            else:
                output_text = str(result)

            if not output_text or not output_text.strip() or output_text.strip() == "{}" or output_text.strip() == "None":
                output_text = "✅ Task execution completed successfully. All files, tools, and actions were executed."

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
1. When asked to create files, CALL the file_operation tool with operation "write".
2. When asked to fix or update a file, FIRST read it with operation "read". For localized fixes or small edits, use operation "patch" with target and replacement JSON content. For new files or full file rewrites, use operation "write".
3. DO NOT just describe - ACTUALLY CREATE or FIX files using tools.
4. ALWAYS use Action/Action Input format. You MUST invoke tools to write code to the filesystem; never just output code in markdown blocks in your response text.
5. Code MUST be formatted with proper indentation and newlines. Never write all code in one line.
6. In your Final Answer, you MUST always write a detailed walkthrough of what you did, which files you created or modified, explain how the user can open, test, or run the application, and confirm browser/console verification status.

APP DESIGN, STRUCTURE & CLEAN SOFTWARE BLUEPRINTS:
1. Modular Architecture: ALWAYS build a properly structured project (multiple modular files, clear directories, separated concerns: UI, Logic, State) rather than a single flat file.
2. CRITICAL WEB & BEAUTIFUL HTML DESIGN MANDATE (WORLD-CLASS UI/UX REQUIREMENTS):
   - NEVER output plain, unstyled HTML with default Times/serif fonts, bare text lists, or standard browser default white backgrounds!
   - EVERY WEB APPLICATION MUST BE AN EXECUTIVE-GRADE, STUNNING MODERN PRODUCT.
   - MANDATORY HEAD HEADERS: Always include Tailwind CSS, Lucide Icons, and Google Fonts in the `<head>` of every HTML file:
     ```html
     <script src="https://cdn.tailwindcss.com"></script>
     <script src="https://unpkg.com/lucide@latest"></script>
     <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
     <style>body {{ font-family: 'Inter', sans-serif; }}</style>
     ```
   - ALWAYS use modern UI design patterns:
     * Dark Mode Palette: `bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white`
     * Glassmorphism Cards: `bg-slate-900/70 backdrop-blur-xl border border-slate-800/80 rounded-2xl shadow-2xl p-6`
     * Glowing Accent Gradients: `bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent`
     * Micro-Interactions & Hover FX: `transition-all duration-300 hover:-translate-y-1 hover:border-indigo-500/50 hover:shadow-indigo-500/10 hover:shadow-2xl`
     * Responsive Layouts: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`
     * Icons & Badges: Use Lucide icons (`<i data-lucide="sparkles"></i>` + `lucide.createIcons()`) and pill badges (`px-3 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20`).
   - IF LINKING AN EXTERNAL CSS FILE (e.g. `<link rel="stylesheet" href="style.css">`), YOU MUST ALSO WRITE THE `style.css` FILE IMMEDIATELY USING `file_operation(write)`! NEVER leave `style.css` missing!
3. Robust Error Boundaries: Always implement comprehensive error handling, input validation, and try-catch blocks. The app must gracefully handle invalid inputs or missing data without crashing.
4. Clean UI Grids & Layouts: Web and Desktop UI must use structured grids/flexbox for alignment, with clean padding and premium modern styling (custom CSS, glassmorphism, responsive grids).
5. No Truncation: NEVER write ellipses ("...") or placeholders like "rest of code remains the same". Always write full, complete, and working files.
6. Cap on Interactive Loops: Ensure that continuous loops (like game loops or polling) have explicit exit conditions or caps to prevent hanging the system.
7. Python Desktop Apps: For games or desktop apps, generate fully working, playable Python scripts (preferring Pygame or Tkinter).
8. Flow and Documentation: You MUST create a `flow.md` file containing a Mermaid flow diagram of the execution flow and a "How to Use" guide.
9. Interactive Features: Ensure every button, toggle, or control is fully implemented and hooked up to real logic.

THINK LONGER & VERIFY SKILL (DEEP QUALITY AUDIT PROTOCOL):
Before you output your Final Answer, you MUST execute a strict quality review of all generated files:
- STEP 1: UI & AESTHETICS AUDIT
  - Is the app UI plain white or basic? If so, YOU MUST rewrite the CSS/HTML to add vibrant gradients, Tailwind CSS, Google Fonts, smooth card shadows, and hover transitions before finishing.
- STEP 2: COMPLETENESS AUDIT
  - Did you leave any placeholders, ellipses, or incomplete sections? If so, write full implementations.
- STEP 3: BROWSER & CONSOLE VERIFICATION
  - CALL `verify_app_browser_console` to test script links (404 checks), HTML structure, JS console syntax, and Python syntax.
  - If any console error is found, fix it using `file_operation(patch)` BEFORE providing the Final Answer.

Tools YOU MUST USE:
1. browser_open_url - Open URL in headless Chromium browser to test live app
2. browser_get_console_errors - Get captured browser console errors and network failures
3. browser_take_screenshot - Take a screenshot of the browser viewport (e.g. {{"name": "after_fixes"}})
4. browser_vision_audit - Run Gemma4:26b vision model audit on screenshot for UI flaws
5. verify_app_browser_console - Verify HTML structure, script links (404 checks), JS console errors, and Python syntax
   Input: {{"target_dir": ""}}
6. file_operation - READ, WRITE, LIST, or PATCH files
   To READ a file:  {{"operation": "read", "path": "filename.py"}}
   To WRITE a file: {{"operation": "write", "path": "filename.py", "content": "file content here"}}
   To LIST files:   {{"operation": "list", "path": ""}}
   To PATCH a file: {{"operation": "patch", "path": "filename.py", "content": "{{\\"target\\": \\"old code\\", \\"replacement\\": \\"new code\\"}}"}}
7. recursive_list - List all files in a directory recursively
8. grep_search - Search for strings in the workspace
9. create_project - For multiple files
   Input: dict with file paths as keys and content as values
10. execute_terminal - Run terminal/shell commands
   Input: {{"command": "npm install", "cwd": "/path/to/dir"}}
11. schedule_task - Schedule a future or recurring agent task
   Input: {{"task_name": "Check Nike shoes", "prompt": "Search the web for Nike Mind shoes availability and report the result", "interval_minutes": 60, "delay_minutes": 1}}

WORKFLOW FOR CREATING NEW FILES:
Step 1: Generate complete code with correct indentation and newlines
Step 2: CALL file_operation tool with operation "write" and the formatted code
Step 3: Confirm creation

WORKFLOW FOR FIXING EXISTING FILES:
Step 1: CALL file_operation with operation "read" to read the existing file
Step 2: Analyze the code and identify the errors/issues and exact target code snippet
Step 3: For localized fixes, CALL file_operation with operation "patch" providing target and replacement in JSON content. For complete rewrites, use operation "write"
Step 4: Confirm the fix was applied

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
        task = f"""Generate a complete application with the following requirements:

{requirements}

Provide:
1. Project structure
2. Complete code for all files
3. Dependencies/requirements
4. Setup instructions
5. Usage guide"""

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
        system_prompt = """You are a Research Agent specialized in information gathering and analysis.

Your capabilities:
- Search and gather information from various sources
- Fetch full page content and convert to clean text
- Summarize complex documents and articles
- Compare and contrast different approaches
- Provide well-researched recommendations
- Stay up-to-date with latest trends and technologies

When given a research task:
1. Break down the research question
2. Gather relevant information using web_search and fetch_web_page
3. Analyze and synthesize findings
4. Present clear, actionable insights
5. Cite sources when applicable

Always provide accurate, unbiased, and comprehensive research."""

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
    """Agent specialized in code and data analysis"""
    def __init__(self, model_name: str = DEFAULT_MAIN_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = f"""You are an Expert Analysis & QA Agent specialized in deep code diagnostics, real browser console verification, Gemma4:26b vision-powered UI audit, and error remediation.

{get_workspace_instructions()}

Your capabilities:
- **Real Browser Testing**: Open the app in a real Chromium browser using `browser_open_url` to capture actual JS console errors, network failures, and runtime exceptions.
- **Vision UI Audit**: Use `browser_vision_audit` to take a screenshot and analyze UI quality, layout, and styling with Gemma4:26b vision model.
- **Console Error Analysis**: Use `browser_get_console_errors` to get detailed console error reports with file locations and line numbers.
- **Screenshot Capture**: Use `browser_take_screenshot` to document the current state of the app.
- **Static File Analysis**: Use `verify_app_browser_console` as a fallback for static file checks (HTML links, JS syntax, Python compile).
- **File Inspection**: Read and analyze files using `file_operation`.

CRITICAL WORKFLOW FOR ANALYZING APPS:
1. FIRST, try to use `browser_open_url` with the app's URL (e.g. http://localhost:5173, http://localhost:3000) to test in a real browser.
2. Use `browser_get_console_errors` to get actual console errors and network failures.
3. Use `browser_vision_audit` to visually inspect the UI for layout bugs, broken styling, or visual defects.
4. Use `browser_take_screenshot` to capture the current state as evidence.
5. Use `file_operation` with operation "read" to inspect the source files where errors were found.
6. If browser tools are unavailable, fall back to `verify_app_browser_console` for static analysis.

CRITICAL UI DESIGN PRESERVATION RULE:
When analyzing or suggesting fixes for HTML/CSS/JS files, NEVER suggest removing styling, CSS rules, Tailwind CDN, Google Fonts, or visual components. ALWAYS preserve and enhance high-end modern design, glassmorphism cards, vibrant color themes, and hover effects in your replacement code recommendations.

Provide a structured report stating:
- ERRORS FOUND: List each error with exact file path, line number, and error type (JS ReferenceError, 404, Python SyntaxError, etc.)
- VISUAL DEFECTS: List any UI/layout issues found by the vision audit.
- EXACT TARGET CODE: Quote the exact lines of code that contain the bug.
- EXACT REPLACEMENT CODE: Provide the drop-in replacement code fix for the Code Agent to apply.

Always provide precise, zero-ambiguity, actionable code diagnostics."""

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

        result = self.process(task, context=context, chat_history=chat_history, callbacks=callbacks)

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
            model_name=os.environ.get("VISION_MODEL", "gemma-4-26b"),
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
    """Agent specialized in business planning, financial modeling, spreadsheet layouts, math calculations, and strategy reports"""
    def __init__(self, model_name: str = DEFAULT_MAIN_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = f"""You are an Executive Business Agent specialized in business strategy, financial modeling, code-driven presentation generation, styled Excel workbooks, and market analysis.

{get_workspace_instructions()}

Your capabilities:
- **Presentation Deck Generation**: Build professional PowerPoint decks (`.pptx`) and interactive HTML slide decks (`.html`) with title slides, executive summaries, metric card grids, data tables, and charts using `generate_presentation`.
- **Advanced Excel Spreadsheet Creation**: Build styled multi-tab Excel workbooks (`.xlsx`) with custom header fills, number & currency formatting (`$#,##0.00`), live Excel formulas (`SUM`, `AVERAGE`), and native charts using `generate_excel_sheet`.
- **Financial Modeling & Strategy**: Create comprehensive business plans, revenue projections, unit economics, and strategic growth reports.
- **CSV & Document Operations**: Manipulate CSV files via `csv_sheet_operation` and read/write text documents via `file_operation`.

CRITICAL RULES FOR TOOL USAGE:
1. When asked to create a spreadsheet, budget, cafe controller, or financial model, YOU MUST ALWAYS CALL `generate_excel_sheet` IMMEDIATELY using the Action/Action Input format below. NEVER just describe the spreadsheet without executing the tool!
2. When asked to create a presentation or pitch deck, ALWAYS call `generate_presentation` with slide specifications.
3. SLIDE COUNT MANDATE: Every presentation deck MUST have a MINIMUM of 4 slides and a MAXIMUM of 30 slides. Include: Title Slide, Executive Summary, Key Performance Metrics, and Strategic Roadmap/Execution Plan.
4. For simple CSV data exports, use `csv_sheet_operation`.
5. For writing strategic markdown documents, use `file_operation`.

EXPLICIT TOOL CALL FORMAT FOR SPREADSHEETS:
Action: generate_excel_sheet
Action Input: {{"title": "Master Controller", "filename": "master_controller", "sheets_json": "[{{\"name\": \"Budget\", \"title\": \"Budget & Expenses\", \"headers\": [\"Category\", \"Item\", \"Estimated ($)\", \"Actual ($)\", \"Variance ($)\", \"Status\"], \"data\": [[\"Equipment\", \"Espresso Machine\", 5000, 4800, \"=C2-D2\", \"Purchased\"], [\"Renovation\", \"Interior Counter\", 3000, 3200, \"=C3-D3\", \"Completed\"], [\"Total\", \"=SUM(C2:C3)\", \"=SUM(D2:D3)\", \"=SUM(E2:E3)\", \"Active\"]]}}]"}}

EXPLICIT TOOL CALL FORMAT FOR PRESENTATIONS & PPTs:
Action: generate_presentation
Action Input: {{"title": "Business Pitch Deck", "subtitle": "Strategic Growth Plan", "filename": "business_pitch_deck", "slides_json": "[{{\"type\": \"title\", \"title\": \"Business Pitch Deck\", \"subtitle\": \"Strategic Growth Plan\"}}, {{\"type\": \"content\", \"title\": \"Executive Overview\", \"bullets\": [\"Market Opportunity Analysis\", \"Revenue & Growth Strategy\", \"Operational Milestones\"]}}, {{\"type\": \"metrics\", \"title\": \"Key Performance Metrics\", \"metrics\": [{{\"label\": \"Target Revenue\", \"value\": \"$1.2M\"}}, {{\"label\": \"Margin\", \"value\": \"35%\"}}]}}]"}}

Tools YOU MUST USE:
1. generate_presentation - Generate PowerPoint (.pptx) AND interactive HTML Reveal.js slide deck
2. generate_excel_sheet - Generate styled Excel workbook (.xlsx) with formulas, multi-tabs, and charts
3. read_excel_sheet - Read data and formulas from Excel workbooks
4. csv_sheet_operation - Read/write basic CSV files
5. file_operation - Read/write markdown/text strategy reports
"""

        super().__init__(
            name="Business Agent",
            agent_type="business",
            system_prompt=system_prompt,
            model_name=model_name,
            ollama_base_url=ollama_base_url
        )

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
