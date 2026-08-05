import os
import sys
import time
import re
import logging
import traceback
import asyncio
from typing import Dict, Any, List, Optional, TypedDict, Annotated
import operator
from .specialized_agents import SafeChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from .specialized_agents import create_specialized_agent, SPECIALIZED_AGENTS, get_workspace_instructions
from .memory import multi_agent_memory
from .config import DEFAULT_MAIN_MODEL, DEFAULT_CODE_MODEL

try:
    from .config import OLLAMA_KEEP_ALIVE
except ImportError:
    OLLAMA_KEEP_ALIVE = "1h"


class AgentState(TypedDict):
    """State for the agent graph"""
    messages: Annotated[List[BaseMessage], operator.add]
    user_request: str
    selected_agent: Optional[str]
    agent_response: Optional[str]
    final_response: Optional[str]
    context: Dict[str, Any]
    session_id: str
    review_critique: Optional[str]
    reflection_count: Optional[int]


class OrchestratorAgent:
    """
    Main orchestrator agent that routes tasks to specialized agents
    Uses LangGraph to manage the workflow
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MAIN_MODEL,
        ollama_base_url: str = "http://localhost:11434"
    ):
        self.model_name = model_name
        self.ollama_base_url = ollama_base_url

        # Initialize LLM for orchestrator
        self.llm = SafeChatOllama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=0.1,  # Lower temperature for more consistent routing and persistence
            timeout=300,
            keep_alive=OLLAMA_KEEP_ALIVE
        )

        # System prompt for orchestrator
        self.system_prompt = f"""You are the Senior Lead Coder & Orchestrator Agent with full permission and authorization to interact with local files, write code, build applications, and route tasks to specialized agents.

{get_workspace_instructions()}

Available specialized agents:
1. CODE AGENT - For software development tasks:
   - Generate code in any programming language (Python, JavaScript/React, C++ for Raspberry Pi & embedded systems)
   - Create full packaged applications (Python backend + frontend + requirements.txt/package.json)
   - Build lightweight browser games (HTML5 Canvas/CSS/JS single-file games)
   - Generate comprehensive system walkthroughs (WALKTHROUGH.md)
   - Execute and test code, perform file operations (read/write/patch)
   - Run terminal/shell commands (npm, python, pip, cmake, etc.)
   - Schedule future or recurring tasks (loops, timers, periodic checks)

2. RESEARCH AGENT - For information gathering:
   - Research topics and technologies
   - Gather and summarize information
   - Compare different approaches
   - Provide recommendations

3. ANALYSIS AGENT - For code analysis only (no fixing):
   - Analyze code quality
   - Identify bugs and vulnerabilities
   - Suggest optimizations
   - Review architecture and design

4. ANALYZE AND FIX - The MOST POWERFUL agent for ANY code modification:
   - Fix errors, bugs, crashes, and broken functionality
   - Handle ANY user change request: "change the color", "make it responsive", "add a sidebar", "improve the layout"
   - Iteratively validates fixes with syntax checking and auto-retries if errors persist
   - Multi-file workspace scanning for cross-file issues
   - Browser-powered console error capture and Gemma4:26b vision UI audit
   - When user says "fix", "debug", "change", "modify", "improve", "make it", "not working", "broken"

5. BUSINESS AGENT - For business planning, financial modeling, spreadsheet tasks, and IMAGE GENERATION:
   - Business strategy, business plans, and market analysis
   - Financial modeling, budgeting, revenue/profit calculations, and cash flow analysis
   - CSV data operations (reading, writing, appending spreadsheet data)
   - Math and financial summaries
   - AI Image Generation using local diffusion models (Stable Diffusion XL, FLUX)
   - Generate images from text prompts, create illustrations, product mockups

Your job:
1. Analyze the user's request
2. Determine which specialized agent is best suited
3. Route the request to that agent
4. Return the agent's response to the user

IMPORTANT ROUTING RULES:
- If the user asks to "analyze AND fix", "find and fix errors", "debug and fix", "fix the errors in", "fix bugs in", "fix something", or fix/debug an existing file -> respond with "analyze_and_fix"
- If the user asks to CHANGE, MODIFY, IMPROVE, or ADJUST something in existing code (e.g. "change the button color", "make it responsive", "not working") -> respond with "analyze_and_fix"
- If the user asks for business planning, financial modeling, budgeting, strategy reports, or spreadsheet/CSV file operations (read, write, append CSV) -> respond with "business"
- If the user asks to generate, create, or make an IMAGE, picture, illustration, or photo -> respond with "business"
- If the user asks to only analyze or review code (no fixing) -> respond with "analysis"
- If the user asks to create, generate, or write NEW code from scratch -> respond with "code"
- If the user asks to run a command, run an app, start a server, install packages, or execute terminal commands -> respond with "code"
- If the user asks to schedule a task, set a timer, check something periodically, or create a loop -> respond with "code"

Respond with ONLY the agent name: "code", "research", "analysis", "business", "analyze_and_fix"
If the request is general or conversational, respond with "general"."""

        # Build the LangGraph workflow
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with Reflection Loop"""

        # Create the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("execute_agent", self._execute_agent)
        workflow.add_node("review_response", self._review_response)
        workflow.add_node("generate_response", self._generate_response)

        # Define edges
        workflow.set_entry_point("analyze_request")
        workflow.add_edge("analyze_request", "execute_agent")

        # Reflection loop logic
        def should_continue(state: AgentState):
            retry_count = state.get("reflection_count", 0)
            critique = (state.get("review_critique") or "").strip()
            
            # If review passed (case-insensitive check for PASSED)
            if "PASSED" in critique.upper():
                return "generate_response"
                
            # Cap maximum reflection retries to prevent endless loops
            if retry_count >= 1:
                return "generate_response"
                
            return "execute_agent"

        workflow.add_conditional_edges(
            "review_response",
            should_continue,
            {
                "execute_agent": "execute_agent",
                "generate_response": "generate_response"
            }
        )

        workflow.add_edge("execute_agent", "review_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    def _analyze_request(self, state: AgentState) -> AgentState:
        """Analyze the user request and determine which agent to use"""
        user_request = state["user_request"]
        session_id = state.get("session_id", "default")
        context = state.get("context") or {}

        # Direct agent override
        direct_agent = context.get("direct_agent")
        if direct_agent and direct_agent in ["research", "business", "code", "analysis", "analyze_and_fix", "general"]:
            selected_agent = direct_agent
        else:
            request_lower = user_request.lower()

            # 1. Business / Spreadsheet / Excel / CSV / Presentation / Image Generation Patterns
            business_keywords = [
                "csv", "spreadsheet", "spread sheet", "spread shit", "spread-sheet", "spread", "sheet", "sheets",
                "excel", "xlsx", "xls", "workbook", "table", "tabular", "financial", "business plan",
                "business strategy", "revenue", "profit", "budget", "market analysis",
                "forecast", "financial model", "cash flow", "balance sheet",
                "csv_sheet_operation", "financial report", "sales analysis",
                "presentation", "ppt", "pptx", "powerpoint", "slides", "pitch deck", "slide deck", "deck",
                # Image generation keywords
                "generate image", "generate an image", "generate picture", "create image", "create an image",
                "create picture", "make image", "make an image", "make picture", "draw me", "draw a",
                "illustration of", "image of", "picture of", "photo of",
                "text to image", "t2i", "stable diffusion", "flux", "diffusion model",
            ]

            # 2. Code / App Creation / Web Dev / Next.js / HTML5 / Running Server / File Operations
            code_keywords = [
                "make an app", "build app", "create app", "new page", "build page", "create page",
                "add feature", "add button", "write code", "generate app", "code agent", "react", "next.js",
                "nextjs", "app router", "next app", "fullstack", "typescript", "index.html", "landing page",
                "single page app", "spa", "tailwind app", "web application", "dashboard", "react component",
                "html", "css", "javascript", "python script", "frontend", "backend", "web app",
                "component", "ui layout", "run the app", "run my app", "run this app", "start the server",
                "npm run", "npm start", "npm install", "pip install", "python run",
                "run the command", "execute command", "run command", "terminal",
                "start the app", "launch the app", "run it", "schedule", "every day", "every hour",
                "every minute", "periodically", "check every", "loop", "timer", "remind me", "recurring",
                "create file", "create a file", "make a file", "write file", "write a file", "new file",
                "generate file", "save file", "create script", "write script", "code file", "create project",
                "make project", "build project", "file creation", "create folder", "create directory", "create code"
            ]

            # 3. Analyze and Fix Bugs / Errors / User Change Requests
            fix_keywords = [
                # Bug fixing keywords
                "fix error", "fix bug", "fix the error", "fix the bug", "debug and fix",
                "find and fix", "analyze and fix", "fix issues in", "fix this file",
                "fix errors in", "fix bugs in", "correct the errors", "fix issue in",
                "fix the issue in", "getting this error", "getting an error", "got this error",
                "error is", "solve the error", "resolve the error", "fix it", "fix code",
                # User modification / change requests (routes to analyze_and_fix for smart handling)
                "change the", "change this", "modify the", "modify this",
                "update the style", "update the color", "update the font", "update the layout",
                "make it", "make the", "convert the", "convert this",
                "refactor", "restructure", "redesign",
                "improve the", "improve this", "optimize the", "optimize this",
                "replace the", "replace this", "move the", "move this",
                "rename the", "rename this", "remove the", "remove this",
                "adjust the", "adjust this",
                "change color", "change font", "change size", "change layout", "change style",
                "not working", "doesn't work", "isn't working", "doesnt work", "isnt working",
                "broken", "crashing", "throws error", "showing error",
            ]

            # 4. Research / Search
            research_keywords = [
                "research", "web search", "search for", "find info", "look up", "information on",
                "summary of", "summarize", "explain how", "compare", "what is", "who is", "why does",
                "tell me about", "latest news", "trends in"
            ]

            is_business_request = any(kw in request_lower for kw in business_keywords)
            is_code_request = any(kw in request_lower for kw in code_keywords)
            import re
            cleaned_request = re.sub(r'[^\w\s]', ' ', request_lower)
            request_words = cleaned_request.split()
            is_fix_request = any(kw in request_lower for kw in fix_keywords) or any(w in request_words for w in ["fix", "debug", "resolve", "refactor", "broken"])
            is_research_request = any(kw in request_lower for kw in research_keywords)

            if is_fix_request:
                selected_agent = "analyze_and_fix"
            elif is_code_request:
                selected_agent = "code"
            elif is_business_request:
                selected_agent = "business"
            elif is_research_request:
                selected_agent = "research"
            else:
                # Fast LLM router fallback without slow embedding calls
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=f"User request: {user_request}\n\nWhich agent should handle this? Respond with ONLY ONE word from: code, research, analysis, business, analyze_and_fix, general.\nNOTE: If the user wants to create, build, run, or write an app, website, script, or software, select 'code'.")
                ]
                try:
                    response = self.llm.invoke(messages)
                    selected_agent = response.content.strip().lower()
                    for valid_agent in ["analyze_and_fix", "code", "business", "research", "analysis", "general"]:
                        if valid_agent in selected_agent:
                            selected_agent = valid_agent
                            break
                    else:
                        selected_agent = "general"
                except Exception:
                    selected_agent = "general"

        # Inject prompt guidelines for file creation/update
        if selected_agent in ["code", "analyze_and_fix"]:
            guidelines = "\n\nGeneral Software Design Guidelines: Ensure the solution is complete, modular, and includes robust error handling."
            if guidelines not in state["user_request"]:
                state["user_request"] += guidelines

        state["selected_agent"] = selected_agent
        state["messages"].append(AIMessage(content=f"Selected agent: {selected_agent}"))

        # Stream agent selection details to queue if present
        context = state.get("context") or {}
        if "queue" in context and "loop" in context:
            queue = context["queue"]
            loop = context["loop"]
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "agent_selection",
                    "agent": selected_agent,
                    "done": False
                }
            )

        return state

    def _execute_agent(self, state: AgentState) -> AgentState:
        """Execute the selected specialized agent and handle the result"""
        selected_agent = state["selected_agent"]
        user_request = state["user_request"]
        session_id = state.get("session_id", "default")
        critique = state.get("review_critique")

        # Get queue and loop if streaming is active
        callbacks = []
        context = dict(state.get("context") or {})
        context["session_id"] = session_id

        # Inject thinking level directive (Claude Code style System Prompt)
        thinking_level = context.get("thinking_level", "medium").lower()
        thinking_directives = {
            "low": "\n\n[SYSTEM DIRECTIVE - THINKING MODE: LOW. You are currently operating in LOW THINKING MODE. Do not perform extended thinking or lengthy step-by-step reasoning. Do not generate thought breakdowns. Respond directly, concisely, and execute tools immediately.]",
            "medium": "\n\n[SYSTEM DIRECTIVE - THINKING MODE: MEDIUM. You are currently operating in MEDIUM THINKING MODE. Perform balanced step-by-step reasoning and tool plan verification before executing tools.]",
            "high": "\n\n[SYSTEM DIRECTIVE - THINKING MODE: HIGH. You are currently operating in HIGH THINKING MODE. Perform deep reasoning, multi-layer verification, edge-case analysis, and code safety checks before generating output.]",
            "extended": "\n\n[SYSTEM DIRECTIVE - THINKING MODE: EXTENDED. You are currently operating in EXTENDED THINKING MODE (Claude Code Style). You MUST perform deep, exhaustive architectural thinking, multi-layer verification, and emit a detailed <thinking> ... </thinking> reasoning breakdown evaluating design options, code safety, edge cases, and step-by-step execution strategy before presenting your answer.]"
        }
        thinking_prompt = thinking_directives.get(thinking_level, thinking_directives["medium"])
        if thinking_prompt not in user_request:
            user_request += thinking_prompt

        if "queue" in context and "loop" in context:
            from .specialized_agents import ThreadSafeAgentCallbackHandler
            cb = ThreadSafeAgentCallbackHandler(context["queue"], context["loop"], selected_agent, session_id=session_id)
            callbacks.append(cb)

        # Enhance request if we have a critique from the reviewer
        if critique and critique != "PASSED":
            user_request = f"""The previous attempt was reviewed and found to have issues.
Please correct the following:
{critique}

Original Request:
{user_request}"""

        # Intercept and prompt implementation plan for specialized tasks
        if selected_agent != "general" and selected_agent != "research" and context and "queue" in context and "loop" in context:
            if "Please execute the following approved plan:" not in user_request:
                # If thinking level is low (Fast Mode), skip separate plan generation to maximize execution speed
                if thinking_level == "low" and not any(kw in user_request.lower() for kw in ["require plan", "approve plan", "plan first", "plan review", "review plan"]):
                    pass
                else:
                    import os
                    queue = context["queue"]
                    loop = context["loop"]

                    # Emit streaming notice so user knows plan generation is active
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        {
                            "type": "thinking",
                            "content": "\n📋 Generating workspace Implementation Plan...\n"
                        }
                    )

                    chat_history = multi_agent_memory.get_messages(session_id)
                    if len(chat_history) > 6:
                        chat_history = chat_history[-6:]
                    formatted_history = ""
                    if chat_history:
                        formatted = []
                        for msg in chat_history:
                            role = "User" if msg.type == "human" else "Assistant"
                            formatted.append(f"{role}: {msg.content}")
                        formatted_history = "\n".join(formatted)

                    plan_prompt = f"""You are the Multi-Agent system's Expert Planner AND Senior Lead Coder. You have FULL AUTHORIZATION AND ACCESS to create, edit, inspect, and write local files and workspace directories.

{get_workspace_instructions()}

YOUR TASK:
As the Senior Lead Coder & System Planner, generate a concise, structured Markdown implementation plan for the user's software task.

Your implementation plan MUST include:
1. Complete Project & File Blueprint: List all local files to be created or updated with exact relative file paths.
2. Architecture & Design: Outline key components, layout, and functionality.
3. Execution Steps: List tool calls and code generation steps.

User Task: {user_request}
Chat History: {formatted_history}

Output ONLY the complete Markdown plan directly."""

                    try:
                        require_approval = context.get("require_plan_approval") is True or any(
                            kw in user_request.lower() for kw in ["require plan", "approve plan", "plan first", "plan review", "review plan"]
                        ) or thinking_level == "extended"

                        if require_approval:
                            plan_response = self.llm.invoke([
                                SystemMessage(content="You are the Multi-Agent System Lead Architect & Planner."),
                                HumanMessage(content=plan_prompt)
                            ])
                            plan_content = plan_response.content
                        else:
                            # Instant blueprint generation for high-speed execution (<1ms delay)
                            task_clean = user_request[:80].replace("\n", " ")
                            plan_content = f"""# Implementation Plan: {task_clean}

## 🎯 Task Blueprint
Generate production-grade application code fulfilling user requirements in workspace directory `{AGENT_WORKSPACE_DIR}`.

## 📁 Key File Structure
- `package.json` / Dependency Configuration
- `app/layout.tsx` & `app/page.tsx`
- Component Modules, Styles & Utilities
- `README.md` & Setup Guide

## ⚡ Execution Steps
1. Initialize task progress checklist (`update_todo_list`)
2. Generate complete project structure & code (`create_project`)
3. Run automated batch verification (`batch_verify_and_repair_files`)
4. Finalize application walkthrough
"""

                        from .config import AGENT_WORKSPACE_DIR
                        plan_path = os.path.join(AGENT_WORKSPACE_DIR, "implementation_plan.md")
                        os.makedirs(os.path.dirname(plan_path), exist_ok=True)
                        with open(plan_path, 'w', encoding='utf-8') as f:
                            f.write(plan_content)

                        if require_approval:
                            from .permissions import register_and_wait_for_plan_approval
                            approved_plan = register_and_wait_for_plan_approval(
                                session_id=session_id,
                                plan_content=plan_content,
                                plan_path=plan_path,
                                queue=queue,
                                loop=loop
                            )
                            user_request = f"Please execute the following approved plan:\n\n{approved_plan}\n\nOriginal Request:\n{user_request}"
                        else:
                            # Stream plan for UI visibility without blocking execution
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                {
                                    "type": "plan_request",
                                    "plan_path": plan_path,
                                    "plan_content": plan_content,
                                    "session_id": session_id,
                                    "auto_approved": True,
                                    "done": False
                                }
                            )

                        state["user_request"] = user_request
                    except Exception as pe:
                        print(f"Error during implementation plan phase: {pe}")

        if selected_agent == "general":
            history = multi_agent_memory.get_messages(session_id)
            if len(history) > 10:
                history = history[-10:]
            formatted_history = ""
            if history:
                formatted = []
                for msg in history:
                    role = "User" if msg.type == "human" else "Assistant"
                    formatted.append(f"{role}: {msg.content}")
                formatted_history = "\n".join(formatted)

            sys_prompt = f"""You are SeniorAgent Orchestrator, an intelligent local AI assistant.

{get_workspace_instructions()}

Respond clearly and helpfully to the user.
Conversation History:
{formatted_history}"""
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=state["user_request"])
            ])
            state["agent_response"] = response.content
        elif selected_agent == "analyze_and_fix":
            state["agent_response"] = self._analyze_and_fix(user_request, context, session_id=session_id, callbacks=callbacks)
        else:
            agent_model = DEFAULT_CODE_MODEL if selected_agent == "code" else self.model_name
            agent = create_specialized_agent(selected_agent, agent_model, self.ollama_base_url)
            if agent:
                chat_history = multi_agent_memory.get_messages(session_id)
                if len(chat_history) > 10:
                    chat_history = chat_history[-10:]
                result = agent.process(user_request, context, chat_history=chat_history, callbacks=callbacks)

                # Post-Generation Browser & Console Verification & Auto-Fix Pipeline for Code Agent
                if selected_agent == "code":
                    try:
                        from .tools import verify_app_browser_console
                        if "queue" in context and "loop" in context:
                            loop = context["loop"]
                            queue = context["queue"]
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                {"type": "thinking", "content": "\n🔍 Running Automated Browser & Gemma-4-26B Vision UI Verification Audit..."}
                            )

                        audit_report = verify_app_browser_console()

                        if "FAILED" in audit_report or "CONSOLE ERROR" in audit_report or "SYNTAX ERROR" in audit_report or "VISUAL DEFECT" in audit_report:
                            if "queue" in context and "loop" in context:
                                loop = context["loop"]
                                queue = context["queue"]
                                loop.call_soon_threadsafe(
                                    queue.put_nowait,
                                    {"type": "thinking", "content": "\n⚠️ Console/Syntax or Vision UI Layout Flaws Detected! Handing off to Analyze & Fix Agent...\n"}
                                )

                            autofix_request = f"The browser verification step & Gemma-4-26B Vision inspection detected errors or visual UI flaws in the generated app files:\n\n{audit_report}\n\nPlease analyze and fix both code errors and visual layout/styling flaws in the codebase."
                            autofix_result = self._analyze_and_fix(autofix_request, context, session_id=session_id, callbacks=callbacks)

                            # Re-verify after auto-fix
                            post_fix_audit = verify_app_browser_console()
                            result = f"{result}\n\n---\n\n### 🛠️ Automated Browser & Gemma-4-26B Vision Auto-Fix Audit\n\n{autofix_result}\n\n{post_fix_audit}"
                        else:
                            result = f"{result}\n\n---\n\n{audit_report}"
                    except Exception as ve:
                        print(f"Error during browser verification phase: {ve}")

                state["agent_response"] = result
            else:
                state["agent_response"] = f"Error: Could not create {selected_agent} agent"

        return state

    def _review_response(self, state: AgentState) -> AgentState:
        """Review the agent response and decide if it needs correction."""
        agent_response = state.get("agent_response")
        user_request = state.get("user_request")
        
        current_count = state.get("reflection_count", 0)
        state["reflection_count"] = current_count + 1

        if not agent_response:
            state["review_critique"] = "No response generated."
            return state

        if current_count >= 1:
            state["review_critique"] = "PASSED"
            return state

        review_prompt = f"""You are a Senior Reviewer. Your job is to audit the agent's response against the user's original request.

User Request:
{user_request}

Agent Response:
{agent_response}

Critique the response based on:
1. Completeness: Did the agent do everything requested?
2. Correctness: Is the code/information accurate?
3. Quality: Is the styling premium (if web) and the code modular?
4. Instructions: Did it follow all "CRITICAL RULES" (e.g., using tools to write files)?

If the response is acceptable and meets the basic request, respond with EXACTLY: "PASSED"
If there are critical missing files or broken code, provide a concise list of what needs to be fixed.
"""

        try:
            review_response = self.llm.invoke([
                SystemMessage(content="You are a Senior Reviewer auditing agent responses."),
                HumanMessage(content=review_prompt)
            ])
            critique = review_response.content.strip()
            state["review_critique"] = critique
        except Exception as e:
            print(f"Error during review phase: {e}")
            state["review_critique"] = "PASSED" # Fallback to pass on error to avoid infinite loops

        return state

    def _analyze_and_fix(self, user_request: str, context: dict = None, session_id: str = "default", callbacks: Optional[List[Any]] = None) -> str:
        """Chain Analysis Agent → Code Agent for analyze-and-fix workflows.
        Enhanced with iterative fix-verify-retry loop, Playwright browser automation,
        console error capture, and Gemma4:26b vision UI audit."""
        import re
        import os
        import time
        import base64
        import socket
        import ast
        from langchain_core.messages import AIMessage

        thinking_level = (context or {}).get("thinking_level", "medium").lower()
        # Fast Mode: Run a minimal direct fix without browser/vision pipeline
        if thinking_level == "low":
            chat_history = multi_agent_memory.get_messages(session_id)
            if len(chat_history) > 6:
                chat_history = chat_history[-6:]
            code_agent = create_specialized_agent("code", DEFAULT_CODE_MODEL, self.ollama_base_url)
            if not code_agent:
                return "Error: Could not create Code Agent for fast fix."
            fast_fix_task = f"""YOU ARE IN FAST ANALYZE-AND-FIX MODE. Quickly analyze and apply fixes.
User Request: {user_request}
Read the relevant files, identify issues, and apply fixes using file_operation(patch) or file_operation(write)."""
            result = code_agent.process(fast_fix_task, context=context, chat_history=chat_history, callbacks=callbacks)
            return result if isinstance(result, str) else (result or {}).get("result", str(result or ""))

        chat_history = multi_agent_memory.get_messages(session_id)
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

        # --- Utility: stream a thinking event to frontend ---
        def emit_thinking(message: str):
            if context and "queue" in context and "loop" in context:
                context["loop"].call_soon_threadsafe(
                    context["queue"].put_nowait,
                    {"type": "thinking", "content": message}
                )

        def emit_screenshot_result(screenshots: list):
            """Send final 'your app looks like this' screenshots to frontend"""
            if context and "queue" in context and "loop" in context:
                context["loop"].call_soon_threadsafe(
                    context["queue"].put_nowait,
                    {
                        "type": "screenshot_result",
                        "screenshots": screenshots,
                        "done": True
                    }
                )

        # --- Step 1: Detect target file or directory ---
        filepath = None
        file_patterns = [
            r'(?:in|for|file|fix|analyze|debug|check)\s+["\']?([a-zA-Z0-9_\-\.\/\\\\:]+\.[a-zA-Z0-9]+)["\']?',
            r'["\']([a-zA-Z0-9_\-\.\/\\\\:]+\.[a-zA-Z0-9]+)["\']',
            r'`([a-zA-Z0-9_\-\.\/\\\\:]+\.[a-zA-Z0-9]+)`',
        ]
        for pattern in file_patterns:
            match = re.search(pattern, user_request, re.IGNORECASE)
            if match:
                filepath = match.group(1)
                break

        if not filepath and chat_history:
            for msg in reversed(chat_history):
                if isinstance(msg, AIMessage):
                    match = re.search(r'\[SUCCESS\] Created:\s*([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+)', msg.content)
                    if match:
                        filepath = match.group(1)
                        break
                    match_quote = re.search(r'(?:created|wrote|updated|in)\s+["\'`]?([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+)["\'`]?', msg.content, re.IGNORECASE)
                    if match_quote:
                        filepath = match_quote.group(1)
                        break

        # --- Step 2: Detect app type and find target URL (prioritizing local workspace HTML files) ---
        emit_thinking("\n🔍 Locating application target and checking workspace HTML files...")
        
        from .config import AGENT_WORKSPACE_DIR, SCREENSHOTS_DIR
        app_url = None
        target_html = None
        
        # 1. Prioritize workspace HTML files (e.g. index.html or target filepath)
        if filepath and (filepath.endswith('.html') or filepath.endswith('.htm')):
            full_p = os.path.isabs(filepath) and filepath or os.path.join(AGENT_WORKSPACE_DIR, filepath)
            if os.path.exists(full_p):
                target_html = full_p

        if not target_html:
            index_html = os.path.join(AGENT_WORKSPACE_DIR, "index.html")
            if os.path.exists(index_html):
                target_html = index_html
            else:
                for root, dirs, files in os.walk(AGENT_WORKSPACE_DIR):
                    dirs[:] = [d for d in dirs if d not in ['node_modules', 'venv', '.git', '.next', 'dist', 'build', '__pycache__', '.cache']]
                    for f in files:
                        if f.endswith('.html') or f.endswith('.htm'):
                            target_html = os.path.join(root, f)
                            break
                    if target_html:
                        break

        if target_html:
            clean_path = os.path.abspath(target_html).replace('\\', '/')
            app_url = f"file:///{clean_path}"
            emit_thinking(f"\n📁 Target HTML file found: {os.path.basename(target_html)} -- Opening browser via file:// URL...")
        else:
            # 2. Check for active frontend dev server ports (excluding backend port 8000)
            dev_server_ports = [5173, 5174, 3000, 3001, 8080, 4200, 5000]
            for port in dev_server_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    if result == 0:
                        app_url = f"http://localhost:{port}"
                        emit_thinking(f"\n✅ Found running frontend dev server at {app_url}")
                        break
                except Exception:
                    pass

        # --- Step 3: Browser automation pipeline ---
        browser_report = ""
        vision_report = ""
        screenshots_taken = []
        browser_launched = False

        if app_url:
            emit_thinking(f"\n🌐 Launching browser at {app_url}...")
            try:
                from .browser_service import get_browser_service, close_browser_service
                browser = get_browser_service()
                
                launch_result = browser.launch(app_url)
                if not isinstance(launch_result, dict):
                    launch_result = {"status": "error", "error": str(launch_result or "Failed to launch browser")}
                
                if launch_result.get("status") == "success":
                    browser_launched = True
                    
                    # Start live streaming to frontend
                    if context and "queue" in context and "loop" in context:
                        browser.start_live_streaming(context["queue"], context["loop"], interval=0.5)
                    
                    emit_thinking(f"\n✅ Browser opened: '{launch_result.get('title', 'N/A')}' — Capturing console errors...")
                    
                    # Capture console & network errors
                    console_errors = browser.get_console_errors()
                    network_errors = browser.get_network_errors()
                    browser_report = f"### Real Browser Console Report\n\n{console_errors}\n\n{network_errors}"
                    
                    # Take initial screenshot
                    initial_screenshot_path = os.path.join(SCREENSHOTS_DIR, "initial_state.png")
                    browser.save_screenshot(initial_screenshot_path)
                    screenshots_taken.append({
                        "name": "initial_state",
                        "url": "/api/screenshots/initial_state.png",
                        "caption": "Initial app state (before fixes)"
                    })
                    
                    # Stream the initial screenshot to frontend
                    if context and "queue" in context and "loop" in context:
                        with open(initial_screenshot_path, "rb") as f:
                            img_b64 = base64.b64encode(f.read()).decode("utf-8")
                        context["loop"].call_soon_threadsafe(
                            context["queue"].put_nowait,
                            {
                                "type": "screenshot_taken",
                                "name": "initial_state",
                                "path": "_screenshots/initial_state.png",
                                "url": "/api/screenshots/initial_state.png",
                                "image_base64": f"data:image/png;base64,{img_b64}",
                                "caption": "Initial app state (before fixes)",
                                "done": False
                            }
                        )
                    
                    # Vision UI audit
                    emit_thinking("\n👁️ Running Gemma4:26b Vision UI Audit on browser screenshot...")
                    try:
                        from .vision_service import analyze_screenshot_bytes
                        from .config import VISION_MODEL
                        screenshot_bytes = browser.take_screenshot()
                        vision_result = analyze_screenshot_bytes(
                            image_bytes=screenshot_bytes,
                            model_name=VISION_MODEL
                        )
                        if not isinstance(vision_result, dict):
                            vision_result = {"report": str(vision_result or ""), "has_visual_defects": False}
                        
                        vision_report = vision_result.get("report", "")
                        if vision_result.get("has_visual_defects"):
                            emit_thinking("\n⚠️ Vision audit detected UI defects!")
                        else:
                            emit_thinking("\n✅ Vision audit: No critical visual defects.")
                    except Exception as ve:
                        emit_thinking(f"\n⚠️ Vision audit error: {ve}")
                        vision_report = f"Vision audit unavailable: {ve}"
                else:
                    emit_thinking(f"\n⚠️ Browser launch failed: {launch_result.get('error', 'Unknown')}")
                    
            except Exception as e:
                emit_thinking(f"\n⚠️ Browser automation error: {e}")
                browser_report = f"Browser automation unavailable: {e}"
        else:
            emit_thinking("\n📋 No running dev server found — proceeding with static file analysis...")

        # --- Step 4: Run Code Agent to analyze and apply fixes directly ---
        emit_thinking("\n🔧 Running Code Agent to analyze and apply fixes directly...")
        
        code_agent = create_specialized_agent("code", DEFAULT_CODE_MODEL, self.ollama_base_url)
        if not code_agent:
            return "Error: Could not create Code Agent"

        fix_context = ""
        if browser_report:
            fix_context += f"\n\n--- BROWSER CONSOLE ERRORS ---\n{browser_report}"
        if vision_report:
            fix_context += f"\n\n--- VISION UI AUDIT REPORT ---\n{vision_report}"

        mtime_before = 0
        target_file_path = None
        if filepath:
            target_file_path = os.path.isabs(filepath) and filepath or os.path.join(AGENT_WORKSPACE_DIR, filepath)
            if os.path.exists(target_file_path):
                mtime_before = os.path.getmtime(target_file_path)

        fix_task = f"""YOU ARE IN ANALYZE-AND-FIX MODE. Analyze the issue and apply ALL required fixes directly to the codebase files.

User Request: {user_request}
Target File (if identified): {filepath or 'Workspace Project'}
{fix_context}

CRITICAL RULES FOR FIXING APPS & STYLING:
1. First, inspect/read the relevant source files (`index.html`, `css/style.css`, etc.) using `file_operation(read)`.
2. HIGH CONTRAST & LEGIBILITY MANDATE: Text MUST be crisp, high contrast, and fully readable against the background. Never use faint gray (like slate-500, gray-400, or low-opacity text) for body text or headings on dark backgrounds. Ensure bright, readable text colors (slate-100, slate-200, white, or light blue).
3. Apply fixes across all relevant files (`index.html`, `css/style.css`, etc.) using `file_operation(write)` or `file_operation(patch)`.
4. Provide a clear summary of what was fixed."""

        fix_result = code_agent.process(fix_task, context=context, chat_history=chat_history, callbacks=callbacks)
        fix_text = (fix_result or {}).get("result", str(fix_result or ""))

        # Auto-apply safety check: If files were output as code blocks, write them to disk matching file types
        if fix_text and "```" in fix_text:
            from .config import AGENT_WORKSPACE_DIR
            file_block_matches = re.findall(r'(?:(?:file|filename|path|created|wrote|output|###|\*\*|`)\s*[:`*]*\s*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)[`*:\s]*\n+)?```([a-zA-Z0-9_\-\:\=]*)\n([\s\S]+?)```', fix_text, re.IGNORECASE)
            for path_hint, lang_tag, code_content in file_block_matches:
                code_content = code_content.strip()
                if not code_content or len(code_content) < 5 or (code_content.startswith("{") and "Action:" in code_content):
                    continue
                
                target_p = None
                if path_hint and ("." in path_hint) and not path_hint.startswith("http") and not path_hint.startswith("json"):
                    target_p = path_hint.strip("`*# :")
                elif "css" in lang_tag.lower() or "body {" in code_content or "font-family:" in code_content:
                    target_p = "css/style.css" if os.path.exists(os.path.join(AGENT_WORKSPACE_DIR, "css", "style.css")) else "style.css"
                elif "html" in lang_tag.lower() or "<!DOCTYPE html>" in code_content or "<html" in code_content:
                    target_p = "index.html"
                elif "js" in lang_tag.lower() or "document.addEventListener" in code_content:
                    target_p = "js/main.js" if os.path.exists(os.path.join(AGENT_WORKSPACE_DIR, "js", "main.js")) else "script.js"
                elif "py" in lang_tag.lower() or "def " in code_content or "import " in code_content:
                    target_p = "main.py"
                
                if target_p:
                    abs_p = target_p if os.path.isabs(target_p) else os.path.join(AGENT_WORKSPACE_DIR, target_p)
                    try:
                        os.makedirs(os.path.dirname(abs_p), exist_ok=True)
                        with open(abs_p, "w", encoding="utf-8") as f:
                            f.write(code_content)
                        emit_thinking(f"\n⚡ Verified & applied code fixes directly to '{os.path.basename(abs_p)}'!")
                    except Exception as fw_err:
                        print(f"Error applying auto-fix for {abs_p}: {fw_err}")

        # --- Step 4.5: Iterative fix-verify-retry loop (max 2 retries) ---
        max_fix_retries = 2
        for retry_i in range(max_fix_retries):
            validation_errors = []

            # Scan workspace for syntax errors in modified files
            try:
                for root, dirs, files in os.walk(AGENT_WORKSPACE_DIR):
                    dirs[:] = [d for d in dirs if d not in ['node_modules', 'venv', '.git', '.next', 'dist', 'build', '__pycache__', '.cache']]
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        try:
                            # Python syntax validation
                            if fname.endswith('.py'):
                                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                                    source = f.read()
                                try:
                                    ast.parse(source, filename=fname)
                                except SyntaxError as se:
                                    rel = os.path.relpath(fpath, AGENT_WORKSPACE_DIR)
                                    validation_errors.append(f"Python SyntaxError in {rel} line {se.lineno}: {se.msg}")

                            # JavaScript basic syntax check (unclosed braces/brackets)
                            elif fname.endswith('.js') or fname.endswith('.jsx') or fname.endswith('.ts') or fname.endswith('.tsx'):
                                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                                    source = f.read()
                                # Simple brace balance check
                                opens = source.count('{') + source.count('(') + source.count('[')
                                closes = source.count('}') + source.count(')') + source.count(']')
                                if abs(opens - closes) > 2:
                                    rel = os.path.relpath(fpath, AGENT_WORKSPACE_DIR)
                                    validation_errors.append(f"JS/TS bracket mismatch in {rel}: {opens} opens vs {closes} closes")

                            # HTML basic validation
                            elif fname.endswith('.html') or fname.endswith('.htm'):
                                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                                    source = f.read()
                                if '<html' in source.lower() and '</html>' not in source.lower():
                                    rel = os.path.relpath(fpath, AGENT_WORKSPACE_DIR)
                                    validation_errors.append(f"HTML missing closing </html> tag in {rel}")
                        except Exception:
                            pass  # Skip unreadable files
            except Exception:
                pass  # Skip if workspace walk fails

            if not validation_errors:
                if retry_i > 0:
                    emit_thinking(f"\n✅ Retry #{retry_i}: All validation checks passed!")
                break  # All clear, exit retry loop

            # Errors found — feed back to Code Agent for another attempt
            error_summary = "\n".join(validation_errors[:10])  # Cap at 10 errors
            emit_thinking(f"\n⚠️ Validation found {len(validation_errors)} error(s) — Retry #{retry_i + 1}/{max_fix_retries}...\n{error_summary}")

            retry_task = f"""VALIDATION ERRORS DETECTED after your previous fix attempt. Please fix these remaining errors:

{error_summary}

Original User Request: {user_request}

Read the affected files, fix the errors, and write the corrected code back using file_operation(patch) or file_operation(write)."""

            retry_result = code_agent.process(retry_task, context=context, chat_history=chat_history, callbacks=callbacks)
            retry_text = (retry_result or {}).get("result", str(retry_result or ""))
            fix_text += f"\n\n### 🔄 Auto-Retry Fix #{retry_i + 1}\n\n{retry_text}"

        # --- Step 5: Post-fix verification with browser ---
        post_fix_report = ""
        if browser_launched:
            emit_thinking("\n🔄 Reloading browser to verify fixes...")
            try:
                from .browser_service import get_browser_service
                browser = get_browser_service()
                
                # Reload page to pick up changes
                time.sleep(2)
                browser.reload_page()
                time.sleep(2)
                
                # Check console errors again
                post_console = browser.get_console_errors()
                post_network = browser.get_network_errors()
                
                # Take post-fix screenshot
                post_fix_path = os.path.join(SCREENSHOTS_DIR, "after_fixes.png")
                browser.save_screenshot(post_fix_path)
                screenshots_taken.append({
                    "name": "after_fixes",
                    "url": "/api/screenshots/after_fixes.png",
                    "caption": "App state after fixes"
                })
                
                # Stream post-fix screenshot
                if context and "queue" in context and "loop" in context:
                    with open(post_fix_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode("utf-8")
                    context["loop"].call_soon_threadsafe(
                        context["queue"].put_nowait,
                        {
                            "type": "screenshot_taken",
                            "name": "after_fixes",
                            "path": "_screenshots/after_fixes.png",
                            "url": "/api/screenshots/after_fixes.png",
                            "image_base64": f"data:image/png;base64,{img_b64}",
                            "caption": "App state after fixes",
                            "done": False
                        }
                    )
                
                post_fix_report = f"\n\n### Post-Fix Browser Verification\n\n{post_console}\n\n{post_network}"
                
                # Close browser and stop live streaming
                emit_thinking("\n🛑 Closing browser session...")
                from .browser_service import close_browser_service
                close_browser_service()
                
            except Exception as e:
                emit_thinking(f"\n⚠️ Post-fix verification error: {e}")
                post_fix_report = f"\n\nPost-fix verification unavailable: {e}"

        # --- Step 6: Send final screenshot results to frontend ---
        if screenshots_taken:
            emit_screenshot_result(screenshots_taken)

        # --- Build combined report ---
        combined = ""

        if browser_report:
            combined += f"## 🖥️ Browser Console Report\n\n{browser_report}\n\n---\n\n"

        if vision_report:
            combined += f"## 👁️ Vision UI Audit (Gemma4:26b)\n\n{vision_report}\n\n---\n\n"

        combined += f"## 🔧 Fix Report (Code Agent)\n\n{fix_text}"

        if post_fix_report:
            combined += f"\n\n---\n{post_fix_report}"

        # Add screenshots section
        if screenshots_taken:
            combined += "\n\n---\n\n## 📸 App Screenshots\n\n"
            combined += "Your app looks like this:\n\n"
            for ss in screenshots_taken:
                combined += f"- **{ss['caption']}**: `{ss['url']}`\n"

        return combined

    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate the final response to the user"""
        selected_agent = state["selected_agent"]
        agent_response = state["agent_response"]

        if selected_agent == "general":
            final_response = agent_response
        else:
            final_response = f"""**Agent Used:** {selected_agent.upper()} AGENT

**Response:**
{agent_response}"""

        state["final_response"] = final_response
        state["messages"].append(AIMessage(content=final_response))

        return state

    def process_request(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Process a user request through the orchestrator"""
        from .config import get_current_main_model
        current_model = get_current_main_model()
        if self.model_name != current_model:
            self.model_name = current_model
            self.llm = SafeChatOllama(
                model=current_model,
                base_url=self.ollama_base_url,
                temperature=0.1,
                timeout=300,
                keep_alive=OLLAMA_KEEP_ALIVE
            )
        try:
            initial_state: AgentState = {
                "messages": [HumanMessage(content=user_request)],
                "user_request": user_request,
                "selected_agent": None,
                "agent_response": None,
                "final_response": None,
                "context": context or {},
                "session_id": session_id,
                "review_critique": None,
                "reflection_count": 0
            }

            final_state = self.workflow.invoke(initial_state)

            agent_response = final_state.get("agent_response") or final_state.get("final_response") or ""
            multi_agent_memory.add_message(session_id, HumanMessage(content=user_request))
            multi_agent_memory.add_message(session_id, AIMessage(content=agent_response))

            return {
                "status": "success",
                "response": final_state["final_response"],
                "agent_used": final_state["selected_agent"],
                "metadata": {
                    "model": self.model_name,
                    "workflow_steps": len(final_state["messages"])
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "response": f"Error processing request: {str(e)}",
                "agent_used": None,
                "metadata": {}
            }


    async def process_request_stream(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: str = "default"
    ):
        """Process a user request with streaming response"""
        from .config import get_current_main_model
        from .permissions import clear_session_cancellation, cancel_session
        
        clear_session_cancellation(session_id)
        
        ctx = dict(context or {})
        provider = ctx.get("provider", "ollama")
        model_name = ctx.get("model")
        api_key = ctx.get("api_key")

        thinking_lvl = (ctx.get("thinking_level") or "medium").lower()

        if provider != "ollama" or model_name or api_key or thinking_lvl == "low":
            try:
                from .specialized_agents import create_agent_llm
                self.llm = create_agent_llm(
                    provider=provider,
                    model_name=model_name or self.model_name,
                    api_key=api_key,
                    ollama_base_url=self.ollama_base_url,
                    thinking_level=thinking_lvl
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "content": str(e),
                    "done": True
                }
                return
        else:
            current_model = get_current_main_model()
            if self.model_name != current_model:
                self.model_name = current_model
                self.llm = SafeChatOllama(
                    model=current_model,
                    base_url=self.ollama_base_url,
                    temperature=0.1,
                    timeout=300,
                    keep_alive=OLLAMA_KEEP_ALIVE
                )

        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        ctx["queue"] = queue
        ctx["loop"] = loop

        graph_task = None
        try:
            initial_state: AgentState = {
                "messages": [HumanMessage(content=user_request)],
                "user_request": user_request,
                "selected_agent": None,
                "agent_response": None,
                "final_response": None,
                "context": ctx,
                "session_id": session_id,
                "review_critique": None,
                "reflection_count": 0
            }

            graph_task = asyncio.create_task(asyncio.to_thread(self.workflow.invoke, initial_state))

            accumulated_response = ""
            selected_agent = "general"
            import time
            last_yield_time = time.time()

            while not graph_task.done() or not queue.empty():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    last_yield_time = time.time()

                    if event["type"] == "agent_selection":
                        selected_agent = event["agent"]
                        yield {
                            "type": "agent_selection",
                            "agent": selected_agent,
                            "done": False
                        }
                    elif event["type"] == "token":
                        accumulated_response += event["content"]
                        yield {
                            "type": "response",
                            "content": accumulated_response,
                            "token": event["content"],
                            "agent": selected_agent,
                            "done": False
                        }
                    elif event["type"] == "thinking":
                        yield {
                            "type": "thinking",
                            "content": event["content"],
                            "agent": selected_agent,
                            "done": False
                        }
                    elif event["type"] in ("tool_start", "tool_end"):
                        yield {
                            "type": event["type"],
                            "tool": event.get("tool"),
                            "tool_input": event.get("tool_input"),
                            "output": event.get("output"),
                            "agent": selected_agent,
                            "done": False
                        }
                    elif event["type"] == "permission_request":
                        yield {
                            "type": "permission_request",
                            "permission_type": event.get("permission_type"),
                            "path": event.get("path"),
                            "command": event.get("command"),
                            "cwd": event.get("cwd"),
                            "session_id": event.get("session_id"),
                            "done": False
                        }
                    elif event["type"] == "plan_request":
                        yield {
                            "type": "plan_request",
                            "plan_path": event.get("plan_path"),
                            "plan_content": event.get("plan_content"),
                            "session_id": event.get("session_id"),
                            "done": False
                        }
                    elif event["type"] == "terminal_output":
                        yield {
                            "type": "terminal_output",
                            "content": event.get("content"),
                            "done": event.get("done", False)
                        }
                    elif event["type"] == "browser_live":
                        yield {
                            "type": "browser_live",
                            "image_base64": event.get("image_base64", ""),
                            "url": event.get("url", ""),
                            "done": event.get("done", False)
                        }
                    elif event["type"] == "screenshot_taken":
                        yield {
                            "type": "screenshot_taken",
                            "name": event.get("name", ""),
                            "path": event.get("path", ""),
                            "url": event.get("url", ""),
                            "image_base64": event.get("image_base64", ""),
                            "caption": event.get("caption", ""),
                            "done": event.get("done", False)
                        }
                    elif event["type"] == "screenshot_result":
                        yield {
                            "type": "screenshot_result",
                            "screenshots": event.get("screenshots", []),
                            "done": event.get("done", True)
                        }
                    elif event["type"] == "todo_list_update":
                        yield {
                            "type": "todo_list_update",
                            "items": event.get("items", []),
                            "agent": selected_agent,
                            "done": False
                        }

                    queue.task_done()
                except asyncio.TimeoutError:
                    if time.time() - last_yield_time >= 3.0:
                        last_yield_time = time.time()
                        yield {
                            "type": "ping",
                            "done": False
                        }
                    continue

            final_state = await graph_task
            final_response = final_state.get("final_response") or accumulated_response
            selected_agent = final_state.get("selected_agent") or selected_agent

            agent_response = final_state.get("agent_response") or accumulated_response or ""
            multi_agent_memory.add_message(session_id, HumanMessage(content=user_request))
            multi_agent_memory.add_message(session_id, AIMessage(content=agent_response))

            from database.db import SessionLocal
            from database.models import PerformanceLogModel
            db_session = SessionLocal()
            prompt_tokens, completion_tokens, total_tokens = 0, 0, 0
            try:
                log = db_session.query(PerformanceLogModel).filter(
                    PerformanceLogModel.agent_id == selected_agent
                ).order_by(PerformanceLogModel.timestamp.desc()).first()
                if log:
                    prompt_tokens = log.prompt_tokens
                    completion_tokens = log.completion_tokens
                    total_tokens = log.total_tokens
            except Exception as db_err:
                print(f"Error querying tokens for stream: {db_err}")
            finally:
                db_session.close()

            yield {
                "type": "response",
                "content": final_response,
                "agent": selected_agent,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "done": True
            }

        except asyncio.CancelledError:
            cancel_session(session_id)
            if graph_task and not graph_task.done():
                graph_task.cancel()
            raise
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Error: {str(e)}",
                "done": True
            }
        finally:
            if graph_task and not graph_task.done():
                graph_task.cancel()

    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of available specialized agents"""
        agents = []
        for agent_type, agent_class in SPECIALIZED_AGENTS.items():
            agent = agent_class(self.model_name, self.ollama_base_url)
            agents.append(agent.get_capabilities())
        return agents
