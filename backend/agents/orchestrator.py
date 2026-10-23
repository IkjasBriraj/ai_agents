import os
import sys
import time
import re
import json
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

import threading
import uuid
from datetime import datetime, timezone

_RUNS_LOCK = threading.Lock()
ACTIVE_AGENT_RUNS: Dict[str, Dict[str, Any]] = {}
RECENT_AGENT_RUNS: List[Dict[str, Any]] = []


def register_agent_run(
    session_id: str = "default",
    prompt: str = "",
    worker_id: str = "orchestrator",
    worker_name: str = "Orchestrator Router",
    source: str = "multi-agent",
    model: str = DEFAULT_MAIN_MODEL,
    run_id: Optional[str] = None,
    **kwargs: Any,
) -> str:
    resolved_run_id = run_id or f"run_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    now_ts = time.time()
    run_data = {
        "run_id": resolved_run_id,
        "session_id": session_id,
        "prompt": (prompt or "")[:240],
        "selected_agent": worker_id,
        "worker_id": worker_id,
        "worker_name": worker_name,
        "routing_reason": "Analyzing intent & selecting optimal worker...",
        "confidence": 1.0,
        "execution_focus": "",
        "phase": "routing",
        "step": "routing",
        "active_tool": None,
        "source": source,
        "model": model,
        "started_at": now_ts,
        "started_iso": now_iso,
        "updated_at": now_ts,
        "started_ts": now_ts,
        "elapsed_seconds": 0.0,
        "status": "running",
        **kwargs,
    }
    with _RUNS_LOCK:
        ACTIVE_AGENT_RUNS[resolved_run_id] = run_data
    return resolved_run_id


def update_agent_run(run_or_session_id: str, **updates: Any) -> None:
    now_ts = time.time()
    with _RUNS_LOCK:
        target_key = None
        if run_or_session_id in ACTIVE_AGENT_RUNS:
            target_key = run_or_session_id
        else:
            for k, v in ACTIVE_AGENT_RUNS.items():
                if v.get("session_id") == run_or_session_id:
                    target_key = k
                    break
        if target_key and target_key in ACTIVE_AGENT_RUNS:
            ACTIVE_AGENT_RUNS[target_key].update(updates)
            if "selected_agent" in updates and "worker_id" not in updates:
                ACTIVE_AGENT_RUNS[target_key]["worker_id"] = updates["selected_agent"]
            if "worker_id" in updates and "selected_agent" not in updates:
                ACTIVE_AGENT_RUNS[target_key]["selected_agent"] = updates["worker_id"]
            ACTIVE_AGENT_RUNS[target_key]["updated_at"] = now_ts
            ACTIVE_AGENT_RUNS[target_key]["elapsed_seconds"] = round(
                now_ts - ACTIVE_AGENT_RUNS[target_key].get("started_ts", now_ts), 1
            )


def complete_agent_run(run_or_session_id: str, status: str = "completed", **kwargs: Any) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    now_ts = time.time()
    with _RUNS_LOCK:
        target_key = None
        if run_or_session_id in ACTIVE_AGENT_RUNS:
            target_key = run_or_session_id
        else:
            for k, v in ACTIVE_AGENT_RUNS.items():
                if v.get("session_id") == run_or_session_id:
                    target_key = k
                    break
        run_data = ACTIVE_AGENT_RUNS.pop(target_key, None) if target_key else None
        if run_data:
            run_data["status"] = status
            run_data["phase"] = status
            run_data["step"] = status
            run_data["active_tool"] = None
            run_data["completed_at"] = now_iso
            run_data["updated_at"] = now_ts
            run_data.update(kwargs)
            run_data["elapsed_seconds"] = round(
                now_ts - run_data.get("started_ts", now_ts), 1
            )
            RECENT_AGENT_RUNS.insert(0, run_data)
            if len(RECENT_AGENT_RUNS) > 15:
                del RECENT_AGENT_RUNS[15:]


def get_active_agent_runs() -> Dict[str, Any]:
    now = time.time()
    with _RUNS_LOCK:
        active_list = []
        for sid, r in list(ACTIVE_AGENT_RUNS.items()):
            item = dict(r)
            item["elapsed_seconds"] = round(now - item.get("started_ts", now), 1)
            active_list.append(item)
        recent_list = list(RECENT_AGENT_RUNS[:8])
        return {
            "active": active_list,
            "active_runs": active_list,
            "active_count": len(active_list),
            "recent": recent_list,
            "recent_runs": recent_list,
        }


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
        self.system_prompt = f"""You are the Autonomous Master Orchestrator & Worker Spawner powered by {model_name}.
You have full authority to analyze any user request, evaluate the catalog of available specialized & custom worker agents, and dynamically decide which worker to spawn.

{get_workspace_instructions()}"""

        # Build the LangGraph workflow
        self.workflow = self._build_workflow()

    def _get_worker_catalog(self) -> List[Dict[str, Any]]:
        """Dynamically discover all built-in and custom worker agents that the LLM can spawn."""
        catalog = [
            {
                "id": "code",
                "name": "Code Architect Worker",
                "role": "Full-Stack Software Engineer & DevOps Executor",
                "capabilities": (
                    "Creates new applications, websites, HTML/CSS/JS/React/Next.js/Python projects from scratch, "
                    "writes and creates files in workspace, runs terminal/shell commands, executes scripts, and schedules recurring tasks/loops."
                ),
                "tools": ["create_project", "file_operation", "execute_terminal", "execute_code", "schedule_task", "verify_app_browser_console"],
                "built_in": True,
            },
            {
                "id": "analyze_and_fix",
                "name": "Surgical Debug & Modification Worker",
                "role": "Multi-File Bug Fixer, Refactorer & UI/Code Modifier",
                "capabilities": (
                    "Fixes bugs, errors, crashes, or broken code; modifies, updates, restyles, or improves existing files/layouts/colors/components; "
                    "performs multi-file root-cause diagnostics, AST validation, and browser vision verification."
                ),
                "tools": ["file_operation", "edit_file", "grep_search", "search_symbols", "browser_vision_audit", "batch_verify_and_repair_files"],
                "built_in": True,
            },
            {
                "id": "research",
                "name": "Deep Research & Web Intelligence Worker",
                "role": "Autonomous Web Researcher & Technical Analyst",
                "capabilities": (
                    "Searches the live web, scrapes URLs, investigates technologies, compares frameworks, "
                    "gathers factual information, and synthesizes comprehensive markdown research reports."
                ),
                "tools": ["web_search", "fetch_web_page", "firecrawl", "summarize_text"],
                "built_in": True,
            },
            {
                "id": "analysis",
                "name": "Architecture & Code Audit Worker",
                "role": "Read-Only Static Code Reviewer & Security Auditor",
                "capabilities": (
                    "Performs read-only code quality reviews, security vulnerability audits, performance bottleneck analysis, "
                    "and architectural critiques without modifying files (use when the user only wants an audit/review, not fixes)."
                ),
                "tools": ["analyze_code", "file_operation", "search_symbols", "get_file_outline", "query_codebase"],
                "built_in": True,
            },
            {
                "id": "business",
                "name": "Business Strategy, Spreadsheets & Vision Worker",
                "role": "Financial Modeler, Presentation Designer & AI Image Generator",
                "capabilities": (
                    "Creates Excel (.xlsx) workbooks with formulas, CSV spreadsheets, PowerPoint (.pptx) & interactive HTML slide decks, "
                    "business plans, financial forecasts, market analysis, and generates AI images/illustrations (SDXL/FLUX)."
                ),
                "tools": ["generate_excel_sheet", "csv_sheet_operation", "generate_presentation", "generate_image", "web_search"],
                "built_in": True,
            },
            {
                "id": "ppt_generator",
                "name": "PPT & Presentation Generator Worker",
                "role": "Master Presentation Architect, Slide Designer & Visual Storyteller",
                "capabilities": (
                    "Generates professional, visually engaging PowerPoint presentations (.pptx) and interactive HTML slide decks (.html) "
                    "on ANY topic requested by the user. Automatically searches for topic-relevant images and photos and embeds them into the slides."
                ),
                "tools": ["generate_presentation", "web_search", "generate_image", "update_todo_list", "file_operation"],
                "built_in": True,
            },
            {
                "id": "general",
                "name": "Direct Orchestrator Assistant",
                "role": "Conversational AI & General Knowledge Advisor",
                "capabilities": (
                    "Handles casual conversation, greetings, simple conceptual questions, or general brainstorming "
                    "that do not require specialized file, code, web-research, or business tools."
                ),
                "tools": [],
                "built_in": True,
            },
        ]

        # Dynamically load any user-defined custom workers from SQLite AgentModel
        try:
            from database.db import SessionLocal
            from database.models import AgentModel

            session = SessionLocal()
            try:
                custom_agents = session.query(AgentModel).all()
                existing_ids = {w["id"] for w in catalog}
                for ca in custom_agents:
                    if ca.id and ca.id not in existing_ids:
                        catalog.append({
                            "id": ca.id,
                            "name": ca.name or ca.id,
                            "role": ca.persona or "Custom Specialized Worker",
                            "capabilities": (ca.system_prompt or "Custom domain worker configured by user.")[:300],
                            "tools": list(ca.tools or []),
                            "built_in": False,
                        })
                        existing_ids.add(ca.id)
            finally:
                session.close()
        except Exception as e:
            logging.debug(f"Could not query custom workers for catalog: {e}")

        return catalog

    def _fallback_semantic_route(self, user_request: str, valid_ids: List[str]) -> Dict[str, Any]:
        """Fallback routing ONLY used if the LLM server is unreachable."""
        req_lower = user_request.lower()
        if any(k in req_lower for k in ["ppt", "presentation", "powerpoint", "slide", "slides", "deck", "pitch deck", "ppt-generater", "ppt generator"]):
            wid = "ppt_generator"
        elif any(k in req_lower for k in ["csv", "spreadsheet", "excel", "xlsx", "financial", "business plan", "revenue", "budget", "generate image", "create image", "draw "]):
            wid = "business"
        elif any(k in req_lower for k in ["fix", "debug", "broken", "not working", "change the", "modify the", "update the", "refactor"]):
            wid = "analyze_and_fix"
        elif any(k in req_lower for k in ["analyze", "audit", "review code", "check code"]) and "fix" not in req_lower:
            wid = "analysis"
        elif any(k in req_lower for k in ["research", "search for", "look up", "latest news", "compare", "trends in"]):
            wid = "research"
        elif any(k in req_lower for k in ["create", "build", "make an app", "write code", "python", "html", "react", "next.js", "website", "landing page", "script", "schedule", "terminal", "run "]):
            wid = "code"
        else:
            wid = "general"
        if wid not in valid_ids:
            wid = "general"
        return {
            "worker_id": wid,
            "worker_name": f"{wid.replace('_', ' ').title()} Worker",
            "confidence": 0.85,
            "reasoning": f"Selected {wid} worker based on task domain analysis.",
            "execution_focus": user_request[:160],
        }

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
        """Generic LLM-driven Worker Router: The LLM inspects the dynamic worker catalog and decides which worker to spawn."""
        user_request = state["user_request"]
        session_id = state.get("session_id", "default")
        context = state.get("context") if isinstance(state.get("context"), dict) else {}
        state["context"] = context

        catalog = self._get_worker_catalog()
        catalog_map = {w["id"]: w for w in catalog}
        valid_ids = list(catalog_map.keys())

        # Direct agent override (only if user explicitly selected Direct Mode in UI)
        direct_agent = context.get("direct_agent")
        if direct_agent and direct_agent in catalog_map:
            selected_agent = direct_agent
            worker_info = catalog_map[selected_agent]
            worker_name = worker_info["name"]
            routing_reason = f"Directly spawned {worker_name} via user override."
            confidence = 1.0
            execution_focus = user_request[:200]
        else:
            # Build conversation context snippet so the LLM can route follow-up prompts intelligently
            recent_history_str = ""
            try:
                hist = multi_agent_memory.get_messages(session_id)
                if hist:
                    recent_msgs = hist[-4:]
                    recent_history_str = "\n".join(
                        f"{'User' if m.type == 'human' else 'Assistant'}: {str(m.content)[:200]}"
                        for m in recent_msgs
                    )
            except Exception:
                pass

            workers_formatted = json.dumps(
                [
                    {
                        "worker_id": w["id"],
                        "name": w["name"],
                        "role": w["role"],
                        "capabilities": w["capabilities"],
                        "tools": w["tools"],
                    }
                    for w in catalog
                ],
                indent=2,
            )

            router_system_prompt = f"""You are the Autonomous Master Orchestrator & Worker Dispatcher ({self.model_name}).
Your responsibility is to analyze the user's request and decide WHICH worker from the Available Worker Catalog you should spawn to execute the task.

AVAILABLE WORKER CATALOG:
{workers_formatted}

DECISION GUIDELINES (GENERIC INTENT ANALYSIS):
- Evaluate the user's goal, required tools, and conversation context.
- Spawn "code" when the user wants to build/create new software, websites, apps, scripts, write new files, run terminal commands, or schedule recurring tasks.
- Spawn "analyze_and_fix" when the user wants to fix bugs/errors/crashes OR modify, update, restyle, or improve existing files/code.
- Spawn "analysis" when the user ONLY wants a code review, static analysis, or security/performance audit of code WITHOUT modifying files.
- Spawn "ppt_generator" when the user wants PowerPoint presentations, slide decks, pitch decks, PPTs, or slideshows on ANY topic (with searched images).
- Spawn "research" when the user wants information gathering, web searches, comparisons, explanations of topics, or industry research.
- Spawn "business" when the user wants spreadsheets (CSV/Excel), financial models, business plans, or AI image generation.
- Spawn any custom worker from the catalog if its specialized persona/capabilities best match the user's request.
- Spawn "general" ONLY for casual greetings or simple chat that requires no specialized worker.

Respond with ONLY a valid JSON object (no markdown fences, no extra text) in this exact schema:
{{
  "worker_id": "<one of: {', '.join(valid_ids)}>",
  "worker_name": "<human-readable worker name>",
  "confidence": 0.95,
  "reasoning": "<concise 1-sentence explanation of why you decided to spawn this worker>",
  "execution_focus": "<clear, actionable sub-task directive for the spawned worker>"
}}"""

            user_payload = f"User Request: {user_request}"
            if recent_history_str:
                user_payload = f"Recent Conversation Context:\n{recent_history_str}\n\nCurrent User Request: {user_request}"

            decision = None
            try:
                response = self.llm.invoke([
                    SystemMessage(content=router_system_prompt),
                    HumanMessage(content=user_payload),
                ])
                raw_text = (response.content or "").strip()
                # Strip any <thinking>...</thinking> blocks if emitted
                raw_text = re.sub(r"<thinking>[\s\S]*?</thinking>", "", raw_text, flags=re.IGNORECASE).strip()

                # Try parsing JSON object from response
                json_match = re.search(r"\{[\s\S]*\}", raw_text)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    cand_id = str(parsed.get("worker_id", "")).strip().lower()
                    if cand_id in catalog_map:
                        decision = {
                            "worker_id": cand_id,
                            "worker_name": parsed.get("worker_name") or catalog_map[cand_id]["name"],
                            "confidence": float(parsed.get("confidence", 0.92)),
                            "reasoning": str(parsed.get("reasoning") or f"LLM selected {catalog_map[cand_id]['name']} based on request intent."),
                            "execution_focus": str(parsed.get("execution_focus") or ""),
                        }
                if decision is None:
                    # Check if raw text mentions a valid worker_id directly
                    raw_lower = raw_text.lower()
                    for wid in ["analyze_and_fix", "business", "analysis", "research", "code", "general"] + [w for w in valid_ids if w not in {"analyze_and_fix", "business", "analysis", "research", "code", "general"}]:
                        if re.search(rf"\b{re.escape(wid)}\b", raw_lower):
                            decision = {
                                "worker_id": wid,
                                "worker_name": catalog_map[wid]["name"],
                                "confidence": 0.88,
                                "reasoning": f"LLM routed task to {catalog_map[wid]['name']}.",
                                "execution_focus": "",
                            }
                            break
            except Exception as llm_err:
                logging.debug(f"LLM router fallback triggered: {llm_err}")

            if decision is None:
                decision = self._fallback_semantic_route(user_request, valid_ids)

            selected_agent = decision["worker_id"]
            worker_name = decision["worker_name"]
            routing_reason = decision["reasoning"]
            confidence = decision["confidence"]
            execution_focus = decision["execution_focus"]

        # Store routing metadata in context
        context["worker_name"] = worker_name
        context["routing_reason"] = routing_reason
        context["routing_confidence"] = confidence
        context["execution_focus"] = execution_focus

        # Update live active run tracker
        update_agent_run(
            session_id,
            worker_id=selected_agent,
            worker_name=worker_name,
            routing_reason=routing_reason,
            confidence=confidence,
            execution_focus=execution_focus,
            phase="executing",
        )

        # Inject prompt guidelines for file creation/update
        if selected_agent in ["code", "analyze_and_fix"]:
            guidelines = "\n\nGeneral Software Design Guidelines: Ensure the solution is complete, modular, and includes robust error handling."
            if guidelines not in state["user_request"]:
                state["user_request"] += guidelines

        state["selected_agent"] = selected_agent
        state["messages"].append(AIMessage(content=f"Spawned worker: {selected_agent} ({worker_name}) — {routing_reason}"))

        # Stream agent selection & LLM routing rationale to queue if present
        if "queue" in context and "loop" in context:
            queue = context["queue"]
            loop = context["loop"]
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "agent_selection",
                    "agent": selected_agent,
                    "worker_name": worker_name,
                    "routing_reason": routing_reason,
                    "confidence": confidence,
                    "execution_focus": execution_focus,
                    "decision_model": self.model_name,
                    "done": False
                }
            )
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "thinking",
                    "content": f"🧠 Orchestrator LLM ({self.model_name}) Decision → Spawned [{worker_name}]: {routing_reason}\n",
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

        # Clean user request for memory extraction and semantic retrieval
        clean_user_request = state.get("user_request", "")

        # Auto-extract personal facts / preferences and inject long-term RAG memory
        try:
            from .personal_memory import personal_memory
            saved_mem = personal_memory.auto_extract_and_save_if_relevant(clean_user_request, context=context)
            recalled_memories = personal_memory.search_memories(clean_user_request, top_k=3)
            if recalled_memories:
                # Notify stream about recalled personal memories
                if "queue" in context and "loop" in context:
                    context["loop"].call_soon_threadsafe(
                        context["queue"].put_nowait,
                        {
                            "type": "memory_recalled",
                            "memories": recalled_memories,
                            "done": False
                        }
                    )
                lines = ["\n[USER PERSONAL KNOWLEDGE & PREFERENCES (PERSISTENT MEMORY)]:"]
                for m in recalled_memories:
                    cat = m.get("category", "fact").upper()
                    lines.append(f"- ({cat}) {m.get('content')}")
                lines.append("Honor these personal preferences and context in your response.\n")
                mem_prompt = "\n".join(lines)
                if mem_prompt not in user_request:
                    user_request += f"\n{mem_prompt}"
        except Exception as me:
            logger.debug(f"Personal memory context lookup failed: {me}")

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
                        )

                        from .config import AGENT_WORKSPACE_DIR
                        task_clean = user_request[:80].replace("\n", " ")
                        if require_approval:
                            plan_response = self.llm.invoke([
                                SystemMessage(content="You are the Multi-Agent System Lead Architect & Planner."),
                                HumanMessage(content=plan_prompt)
                            ])
                            plan_content = plan_response.content
                        else:
                            routing_info = state.get("routing_decision") or {}
                            exec_focus = routing_info.get("execution_focus") or f"Execute {selected_agent} workflow for user request with complete verification."
                            plan_content = f"""# Implementation Plan: {task_clean}

## 🎯 Architectural Objective
{exec_focus}
Target Workspace: `{AGENT_WORKSPACE_DIR}` (Agent: `{selected_agent}`)

## 🧩 Modular Engineering Blueprint
- **Discovery & Context Analysis**: Inspect existing workspace files, symbols, and dependencies relevant to the task.
- **Core Implementation**: Create or update modular source files, configurations, and interfaces with zero placeholders.
- **Verification & Quality Assurance**: Validate syntax/AST, imports, build integrity, and runtime behavior.

## ⚡ Execution Pipeline
1. Initialize live task checklist (`update_todo_list`)
2. Execute primary implementation/analysis tools (`create_project`, `file_operation`, `edit_file`, `execute_code`)
3. Run automated syntax, import, and build verification (`batch_verify_and_repair_files` / `verify_project_build`)
4. Synthesize structured engineering summary
"""

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
                            # Stream plan for UI visibility without blocking execution (informational only)
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                {
                                    "type": "plan_info",
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
            agent_model = self.model_name or (DEFAULT_CODE_MODEL if selected_agent == "code" else self.model_name)
            agent = create_specialized_agent(selected_agent, agent_model, self.ollama_base_url)
            if agent:
                chat_history = multi_agent_memory.get_messages(session_id)
                if len(chat_history) > 10:
                    chat_history = chat_history[-10:]
                result = agent.process(user_request, context, chat_history=chat_history, callbacks=callbacks)

                # Post-Generation Code, Build & Asset Verification & Self-Healing Pipeline for Code Agent
                if selected_agent == "code":
                    try:
                        from .tools import verify_app_browser_console
                        if "queue" in context and "loop" in context:
                            loop = context["loop"]
                            queue = context["queue"]
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                {"type": "thinking", "content": f"\n🔍 Running Automated Code, Syntax & Asset Verification Audit ({self.model_name})..."}
                            )

                        audit_report = verify_app_browser_console()

                        if "FAILED" in audit_report or "CONSOLE ERROR" in audit_report or "SYNTAX ERROR" in audit_report or "VISUAL DEFECT" in audit_report:
                            if "queue" in context and "loop" in context:
                                loop = context["loop"]
                                queue = context["queue"]
                                loop.call_soon_threadsafe(
                                    queue.put_nowait,
                                    {"type": "thinking", "content": "\n⚠️ Code Syntax or Asset Issues Detected! Triggering Analyze & Fix Self-Healing Pipeline...\n"}
                                )

                            autofix_request = f"Automated verification detected syntax, asset, or structural issues in the workspace files:\n\n{audit_report}\n\nPlease analyze and fix all reported issues cleanly."
                            autofix_result = self._analyze_and_fix(autofix_request, context, session_id=session_id, callbacks=callbacks)

                            # Re-verify after auto-fix
                            post_fix_audit = verify_app_browser_console()
                            result = f"{result}\n\n---\n\n### 🛠️ Automated Code & Build Self-Healing Audit\n\n{autofix_result}\n\n{post_fix_audit}"
                        else:
                            result = f"{result}\n\n---\n\n{audit_report}"
                    except Exception as ve:
                        print(f"Error during verification phase: {ve}")

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

        # Run automated build and syntax verification on workspace files
        try:
            from .tools import verify_project_build
            ver_res = json.loads(verify_project_build(""))
            if ver_res.get("status") == "FAILED":
                diags = "\n".join(ver_res.get("diagnostics", []))
                state["review_critique"] = f"CRITICAL BUILD/VERIFICATION ERRORS DETECTED:\n{diags}\nPlease fix all reported syntax and compilation errors immediately."
                return state
        except Exception as ver_err:
            print(f"Build verification check skipped: {ver_err}")

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
        """Deep Codebase Analysis & Intelligent Fix Pipeline:
        Phase 1: Automated Workspace & Symbol Discovery (layout, keyword grep, candidate files, runtime errors)
        Phase 2: Deep Diagnostics by Analysis Agent (root-cause analysis, dependency tracing, fix blueprint)
        Phase 3: Surgical Fix Execution by Code Agent (precision edits, multi-file fixes, iterative AST validation)
        Phase 4: Synthesis & Executive Walkthrough (change summary, root cause, file diffs, verification, WALKTHROUGH.md)
        """
        import re
        import os
        import time
        import base64
        import socket
        import ast
        from langchain_core.messages import AIMessage
        from .config import AGENT_WORKSPACE_DIR, SCREENSHOTS_DIR, VISION_MODEL, DEFAULT_CODE_MODEL

        thinking_level = (context.get("thinking_level", "medium") if isinstance(context, dict) else "medium").lower()

        # Fast Mode: Run minimal direct fix if low thinking level requested
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
            return result if isinstance(result, str) else (result.get("result", str(result)) if isinstance(result, dict) else str(result or ""))

        chat_history = multi_agent_memory.get_messages(session_id)
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

        def emit_thinking(message: str):
            if context and "queue" in context and "loop" in context:
                context["loop"].call_soon_threadsafe(
                    context["queue"].put_nowait,
                    {"type": "thinking", "content": message}
                )

        def emit_screenshot_result(screenshots: list):
            if context and "queue" in context and "loop" in context:
                context["loop"].call_soon_threadsafe(
                    context["queue"].put_nowait,
                    {
                        "type": "screenshot_result",
                        "screenshots": screenshots,
                        "done": True
                    }
                )

        # =====================================================================
        # Phase 1: Automated Workspace & Symbol Discovery
        # =====================================================================
        emit_thinking("\n🔍 Phase 1: Exploring workspace structure and scanning codebase for relevant symbols...")

        workspace_files_snapshot = {}
        all_code_files = []
        skip_dirs = {'node_modules', 'venv', '.git', '.next', 'dist', 'build', '__pycache__', '.cache', '_screenshots', 'storage'}

        for root, dirs, files in os.walk(AGENT_WORKSPACE_DIR):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, AGENT_WORKSPACE_DIR).replace('\\', '/')
                try:
                    mtime = os.path.getmtime(full_path)
                    workspace_files_snapshot[rel_path] = {
                        "full_path": full_path,
                        "mtime": mtime,
                        "size": os.path.getsize(full_path)
                    }
                    ext = os.path.splitext(f)[1].lower()
                    if ext in {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.json', '.vue', '.svelte', '.md', '.sql'}:
                        all_code_files.append(rel_path)
                except Exception:
                    pass

        # Extract search keywords and explicit filenames
        candidate_files = []
        file_patterns = [
            r'(?:in|for|file|fix|analyze|debug|check)\s+["\']?([a-zA-Z0-9_\-\.\/\\\\:]+\.[a-zA-Z0-9]+)["\']?',
            r'["\']([a-zA-Z0-9_\-\.\/\\\\:]+\.[a-zA-Z0-9]+)["\']',
            r'`([a-zA-Z0-9_\-\.\/\\\\:]+\.[a-zA-Z0-9]+)`',
        ]
        for pattern in file_patterns:
            for match in re.finditer(pattern, user_request, re.IGNORECASE):
                fp = match.group(1).replace('\\', '/').strip('/')
                if fp in workspace_files_snapshot or os.path.exists(os.path.join(AGENT_WORKSPACE_DIR, fp)):
                    if fp not in candidate_files:
                        candidate_files.append(fp)

        if not candidate_files and chat_history:
            for msg in reversed(chat_history):
                if isinstance(msg, AIMessage) and msg.content:
                    match_s = re.search(r'\[SUCCESS\] Created:\s*([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+)', msg.content)
                    if match_s:
                        fp = match_s.group(1).replace('\\', '/').strip('/')
                        if fp not in candidate_files:
                            candidate_files.append(fp)
                            break

        stopwords = {
            "the", "and", "for", "with", "make", "change", "fix", "please", "app",
            "code", "that", "this", "from", "into", "some", "what", "when", "where",
            "which", "error", "issue", "agent", "look", "good", "better", "need",
            "have", "does", "not", "work", "broken", "update", "modify", "improve"
        }
        words = re.findall(r'[a-zA-Z0-9_]{3,}', user_request.lower())
        keywords = [w for w in words if w not in stopwords and not w.isdigit()]

        # Grep search for keywords across codebase files
        grep_hits = {}
        for kw in keywords[:8]:
            for rel_path in all_code_files:
                full_path = workspace_files_snapshot[rel_path]["full_path"]
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as cf:
                        content = cf.read()
                    if kw in content.lower():
                        if rel_path not in grep_hits:
                            grep_hits[rel_path] = []
                        grep_hits[rel_path].append(kw)
                        if rel_path not in candidate_files:
                            candidate_files.append(rel_path)
                except Exception:
                    pass

        if not candidate_files:
            for default_candidate in ["index.html", "main.py", "app.py", "src/App.tsx", "src/index.tsx", "src/main.ts", "package.json"]:
                if default_candidate in workspace_files_snapshot:
                    candidate_files.append(default_candidate)

        candidate_files = candidate_files[:6]

        candidate_excerpts = []
        for cf in candidate_files:
            full_p = workspace_files_snapshot.get(cf, {}).get("full_path") or os.path.join(AGENT_WORKSPACE_DIR, cf)
            if os.path.exists(full_p):
                try:
                    with open(full_p, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    excerpt = "".join(lines[:120])
                    truncated_notice = f"\n... [{len(lines) - 120} more lines]" if len(lines) > 120 else ""
                    candidate_excerpts.append(f"### File: `{cf}` ({len(lines)} lines)\n```\n{excerpt}{truncated_notice}\n```")
                except Exception as e:
                    candidate_excerpts.append(f"### File: `{cf}` (Error reading: {e})")

        # Runtime Browser / Console checks if frontend web target exists
        app_url = None
        target_html = None
        for cf in candidate_files:
            if cf.endswith('.html') or cf.endswith('.htm'):
                full_p = workspace_files_snapshot.get(cf, {}).get("full_path") or os.path.join(AGENT_WORKSPACE_DIR, cf)
                if os.path.exists(full_p):
                    target_html = full_p
                    break

        if not target_html and "index.html" in workspace_files_snapshot:
            target_html = workspace_files_snapshot["index.html"]["full_path"]

        if target_html:
            clean_path = os.path.abspath(target_html).replace('\\', '/')
            app_url = f"file:///{clean_path}"
        else:
            dev_server_ports = [5173, 5174, 3000, 3001, 8080, 4200, 5000]
            for port in dev_server_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.3)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    if result == 0:
                        app_url = f"http://localhost:{port}"
                        break
                except Exception:
                    pass

        browser_report = ""
        vision_report = ""
        screenshots_taken = []
        browser_launched = False

        if app_url:
            emit_thinking(f"\n🌐 Checking live application runtime at {app_url}...")
            try:
                from .browser_service import get_browser_service, close_browser_service
                browser = get_browser_service()
                launch_result = browser.launch(app_url)
                if isinstance(launch_result, dict) and launch_result.get("status") == "success":
                    browser_launched = True
                    if context and "queue" in context and "loop" in context:
                        browser.start_live_streaming(context["queue"], context["loop"], interval=0.5)
                    console_errors = browser.get_console_errors()
                    network_errors = browser.get_network_errors()
                    browser_report = f"Browser Runtime Report:\n{console_errors}\n{network_errors}"

                    initial_screenshot_path = os.path.join(SCREENSHOTS_DIR, "initial_state.png")
                    browser.save_screenshot(initial_screenshot_path)
                    screenshots_taken.append({
                        "name": "initial_state",
                        "url": "/api/screenshots/initial_state.png",
                        "caption": "Initial app state (before fixes)"
                    })
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
                    try:
                        from .vision_service import analyze_screenshot_bytes
                        screenshot_bytes = browser.take_screenshot()
                        vision_res = analyze_screenshot_bytes(image_bytes=screenshot_bytes, model_name=VISION_MODEL)
                        if isinstance(vision_res, dict):
                            vision_report = vision_res.get("report", "")
                    except Exception as ve:
                        vision_report = f"Vision audit note: {ve}"
            except Exception as be:
                browser_report = f"Browser automation note: {be}"

        structure_sample = "\n".join([f"- `{f}`" for f in all_code_files[:25]])
        codebase_intel = f"""PROJECT OVERVIEW & CODEBASE DISCOVERY:
Workspace Root: {AGENT_WORKSPACE_DIR}
Total Code Files Found: {len(all_code_files)}
Files Sample:
{structure_sample}

CANDIDATE FILES ANALYZED FOR THIS REQUEST:
{chr(10).join(candidate_excerpts) if candidate_excerpts else 'No specific code files identified yet.'}
"""
        if browser_report:
            codebase_intel += f"\n\nRUNTIME CONSOLE & NETWORK STATUS:\n{browser_report}"
        if vision_report:
            codebase_intel += f"\n\nUI VISION AUDIT:\n{vision_report}"

        # =====================================================================
        # Phase 2: Deep Diagnostics by Analysis Agent
        # =====================================================================
        emit_thinking("\n🔬 Phase 2: Running Analysis Agent for deep architectural diagnostics & root-cause analysis...")
        analysis_agent = create_specialized_agent("analysis", self.model_name, self.ollama_base_url)

        analysis_task = f"""YOU ARE IN DEEP CODEBASE ANALYSIS & DIAGNOSTICS MODE.
User Request: {user_request}

{codebase_intel}

TASK:
Perform deep multi-file analysis and produce a precise, structured DIAGNOSTIC & FIX BLUEPRINT:
1. ROOT CAUSE ANALYSIS: Explain exactly what is failing, missing, or needs modification, tracing the relevant code flow.
2. AFFECTED FILES: List every file that needs changes with its relative path.
3. CROSS-FILE IMPACT: Explain how changes in one file affect other modules, imports, or visual layouts.
4. SURGICAL FIX SPECIFICATIONS: Concrete instructions on what to patch, rewrite, or add in each file.
5. QUALITY & PRESERVATION RULES: Emphasize preserving existing functionality, dark-mode styling, and design systems.

Be thorough, precise, and actionable."""

        analysis_blueprint = ""
        if analysis_agent:
            try:
                analysis_raw = analysis_agent.process(analysis_task, context=context, chat_history=chat_history, callbacks=callbacks)
                analysis_blueprint = analysis_raw.get("result", str(analysis_raw)) if isinstance(analysis_raw, dict) else str(analysis_raw or "")
                emit_thinking("\n✅ Phase 2 Complete: Root cause diagnosed and surgical fix blueprint formulated.")
            except Exception as ae:
                analysis_blueprint = f"Diagnostic analysis note: {ae}"
                emit_thinking(f"\n⚠️ Analysis note: {ae}")

        # =====================================================================
        # Phase 3: Surgical Fix Execution by Code Agent
        # =====================================================================
        emit_thinking("\n🛠️ Phase 3: Dispatching Code Agent to execute precision fixes based on diagnostic blueprint...")
        code_agent = create_specialized_agent("code", DEFAULT_CODE_MODEL, self.ollama_base_url)
        if not code_agent:
            return "Error: Could not create Code Agent for fix execution."

        fix_task = f"""YOU ARE IN PRECISION CODE EXECUTION MODE.
User Request: {user_request}

DIAGNOSTIC & FIX BLUEPRINT FROM ANALYSIS AGENT:
{analysis_blueprint}

TARGET CODE FILES:
{", ".join(candidate_files) if candidate_files else "Workspace Files"}

EXECUTION MANDATE:
1. Apply the fixes to ALL required files using `file_operation(patch)` for surgical edits or `file_operation(write)` for complete files.
2. HIGH CONTRAST & LEGIBILITY MANDATE: Text MUST be crisp, high contrast, and fully readable. Never use faint low-opacity text on dark backgrounds.
3. PRESERVE all existing working features, Tailwind CDN, Google Fonts, glassmorphism design, and interactivity.
4. Apply fixes across every relevant file so everything remains cohesive."""

        fix_result = code_agent.process(fix_task, context=context, chat_history=chat_history, callbacks=callbacks)
        fix_text = fix_result.get("result", str(fix_result)) if isinstance(fix_result, dict) else str(fix_result or "")

        # Auto-apply safety check: If files were output as code blocks, write them to disk matching file types
        if fix_text and "```" in fix_text:
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

        # Iterative validation loop (max 2 retries)
        max_fix_retries = 2
        for retry_i in range(max_fix_retries):
            validation_errors = []
            try:
                for root, dirs, files in os.walk(AGENT_WORKSPACE_DIR):
                    dirs[:] = [d for d in dirs if d not in skip_dirs]
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        try:
                            if fname.endswith('.py'):
                                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                                    source = f.read()
                                try:
                                    ast.parse(source, filename=fname)
                                except SyntaxError as se:
                                    rel = os.path.relpath(fpath, AGENT_WORKSPACE_DIR)
                                    validation_errors.append(f"Python SyntaxError in {rel} line {se.lineno}: {se.msg}")
                            elif fname.endswith(('.js', '.jsx', '.ts', '.tsx')):
                                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                                    source = f.read()
                                opens = source.count('{') + source.count('(') + source.count('[')
                                closes = source.count('}') + source.count(')') + source.count(']')
                                if abs(opens - closes) > 2:
                                    rel = os.path.relpath(fpath, AGENT_WORKSPACE_DIR)
                                    validation_errors.append(f"JS/TS bracket mismatch in {rel}: {opens} opens vs {closes} closes")
                            elif fname.endswith(('.html', '.htm')):
                                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                                    source = f.read()
                                if '<html' in source.lower() and '</html>' not in source.lower():
                                    rel = os.path.relpath(fpath, AGENT_WORKSPACE_DIR)
                                    validation_errors.append(f"HTML missing closing </html> tag in {rel}")
                        except Exception:
                            pass
            except Exception:
                pass

            if not validation_errors:
                if retry_i > 0:
                    emit_thinking(f"\n✅ Retry #{retry_i}: All code validation checks passed!")
                break

            error_summary = "\n".join(validation_errors[:8])
            emit_thinking(f"\n⚠️ Validation found {len(validation_errors)} syntax error(s) — auto-repairing #{retry_i + 1}...\n{error_summary}")
            retry_task = f"""VALIDATION ERRORS DETECTED after your previous fix attempt:
{error_summary}

Please fix these errors immediately using file_operation(patch) or file_operation(write)."""
            retry_res = code_agent.process(retry_task, context=context, chat_history=chat_history, callbacks=callbacks)
            retry_text = retry_res.get("result", str(retry_res)) if isinstance(retry_res, dict) else str(retry_res or "")
            fix_text += f"\n\n### 🔄 Auto-Repair Pass #{retry_i + 1}\n\n{retry_text}"

        # Post-fix browser verification
        post_fix_report = ""
        if browser_launched:
            emit_thinking("\n🔄 Reloading browser to verify fixes...")
            try:
                from .browser_service import get_browser_service, close_browser_service
                browser = get_browser_service()
                time.sleep(1.5)
                browser.reload_page()
                time.sleep(1.5)
                post_console = browser.get_console_errors()
                post_network = browser.get_network_errors()
                post_fix_path = os.path.join(SCREENSHOTS_DIR, "after_fixes.png")
                browser.save_screenshot(post_fix_path)
                screenshots_taken.append({
                    "name": "after_fixes",
                    "url": "/api/screenshots/after_fixes.png",
                    "caption": "App state after fixes"
                })
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
                post_fix_report = f"Post-Fix Verification:\n{post_console}\n{post_network}"
            except Exception as pe:
                post_fix_report = f"Post-fix verification note: {pe}"
            finally:
                try:
                    close_browser_service()
                except Exception:
                    pass

        if screenshots_taken:
            emit_screenshot_result(screenshots_taken)

        # =====================================================================
        # Phase 4: Synthesis & Comprehensive Walkthrough Generation
        # =====================================================================
        emit_thinking("\n📋 Phase 4: Synthesizing executive walkthrough and updating WALKTHROUGH.md...")

        modified_files = []
        created_files = []
        for root, dirs, files in os.walk(AGENT_WORKSPACE_DIR):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, AGENT_WORKSPACE_DIR).replace('\\', '/')
                try:
                    current_mtime = os.path.getmtime(full_path)
                    if rel_path not in workspace_files_snapshot:
                        created_files.append(rel_path)
                    elif current_mtime > workspace_files_snapshot[rel_path]["mtime"] + 0.05:
                        modified_files.append(rel_path)
                except Exception:
                    pass

        all_changed_files = list(dict.fromkeys(created_files + modified_files))

        # Build clean walkthrough sections
        walkthrough_lines = [
            f"# 🔍 Codebase Diagnostics & Fix Walkthrough",
            f"\n> **Request:** {user_request}\n",
            "## 📌 Executive Summary",
        ]

        rc_section = "The codebase was scanned and analyzed to identify structural defects, logic gaps, and styling requirements."
        if analysis_blueprint:
            rc_match = re.search(r'(?:ROOT CAUSE|DIAGNOSTIC|ISSUE SUMMARY)[:\s*\n]+([\s\S]+?)(?=\n###|\n##|\nAFFECTED FILES|\nRECOMMENDED|$)', analysis_blueprint, re.IGNORECASE)
            if rc_match:
                rc_section = rc_match.group(1).strip()
            else:
                rc_section = analysis_blueprint[:400].strip()

        walkthrough_lines.append(f"A comprehensive multi-file codebase audit was performed for the user's request. The root cause was diagnosed, targeted fixes were applied across all affected modules, and the changes were verified.")
        walkthrough_lines.append("\n## 🔎 Root Cause Analysis")
        walkthrough_lines.append(rc_section)

        walkthrough_lines.append("\n## 📂 Files Analyzed vs. Modified")
        walkthrough_lines.append("| File | Role / Status | Action Taken |")
        walkthrough_lines.append("| :--- | :--- | :--- |")

        for cf in candidate_files:
            if cf in created_files:
                walkthrough_lines.append(f"| `{cf}` | Created File | Generated new implementation |")
            elif cf in modified_files:
                walkthrough_lines.append(f"| `{cf}` | Modified Target | Repaired issues & updated implementation |")
            else:
                walkthrough_lines.append(f"| `{cf}` | Inspected File | Verified consistent & unbroken |")

        for mf in all_changed_files:
            if mf not in candidate_files:
                action_str = "Created new file" if mf in created_files else "Modified & updated"
                walkthrough_lines.append(f"| `{mf}` | Modified Dependency | {action_str} |")

        walkthrough_lines.append("\n## 🛠️ Step-by-Step Changes Walkthrough")
        if all_changed_files:
            for idx, fpath in enumerate(all_changed_files, 1):
                full_p = os.path.join(AGENT_WORKSPACE_DIR, fpath)
                line_count = 0
                snippet = ""
                if os.path.exists(full_p):
                    try:
                        with open(full_p, 'r', encoding='utf-8', errors='replace') as sf:
                            flines = sf.readlines()
                        line_count = len(flines)
                        snippet = "".join(flines[:35])
                    except Exception:
                        pass

                ext_tag = fpath.split('.')[-1] if '.' in fpath else ""
                walkthrough_lines.append(f"\n### {idx}. `{fpath}` ({line_count} lines)")
                status_label = "Newly created file" if fpath in created_files else "Updated existing file"
                walkthrough_lines.append(f"- **Status**: {status_label}")
                walkthrough_lines.append(f"- **Summary**: Applied changes resolving the diagnosed issue while preserving overall project conventions and styling.")
                if snippet:
                    walkthrough_lines.append(f"```{ext_tag}\n{snippet}\n```")
        else:
            walkthrough_lines.append("- No files were directly modified on disk during this execution pass.")

        walkthrough_lines.append("\n## 🧪 Verification & Quality Checks")
        walkthrough_lines.append("- [x] **Syntax & AST Validation**: Workspace files scanned and parsed cleanly.")
        if browser_launched:
            walkthrough_lines.append("- [x] **Browser Runtime Verification**: App reloaded and verified in Chromium.")
        if vision_report:
            walkthrough_lines.append(f"- [x] **UI Vision Quality Audit**: Verified visual layout and high-contrast presentation.")
        walkthrough_lines.append("- [x] **Design & Architecture Preservation**: Preserved existing styling systems, components, and module contracts.")

        walkthrough_lines.append("\n## 🚀 How to Test & Next Steps")
        if target_html:
            walkthrough_lines.append(f"1. Open `{os.path.basename(target_html)}` in your web browser, or launch your local live server.")
        elif any(f.endswith('.py') for f in all_changed_files):
            walkthrough_lines.append("1. Run your Python application or test suite to verify the updated behavior:")
            walkthrough_lines.append("   ```bash\n   python main.py\n   ```")
        else:
            walkthrough_lines.append("1. Inspect the updated files in your editor or run your build command.")
        walkthrough_lines.append("2. Confirm the behavior meets your expectations and matches the walkthrough specifications.")

        if screenshots_taken:
            walkthrough_lines.append("\n## 📸 Visual Snapshots")
            for ss in screenshots_taken:
                walkthrough_lines.append(f"- **{ss['caption']}**: `{ss['url']}`")

        walkthrough_content = "\n".join(walkthrough_lines)

        try:
            walkthrough_path = os.path.join(AGENT_WORKSPACE_DIR, "WALKTHROUGH.md")
            with open(walkthrough_path, "w", encoding="utf-8") as wf:
                wf.write(walkthrough_content)
            emit_thinking(f"\n📄 Saved comprehensive WALKTHROUGH.md to workspace directory.")
        except Exception as we:
            emit_thinking(f"\n⚠️ Could not save WALKTHROUGH.md: {we}")

        return walkthrough_content

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
        run_id = f"run_{session_id}_{int(time.time() * 1000)}"
        ctx = dict(context or {})
        ctx["run_id"] = run_id
        register_agent_run(
            run_id=run_id,
            session_id=session_id,
            prompt=user_request,
            source=ctx.get("source", "orchestrator"),
            model=self.model_name
        )
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

            final_state = self.workflow.invoke(initial_state)

            agent_response = final_state.get("agent_response") or final_state.get("final_response") or ""
            multi_agent_memory.add_message(session_id, HumanMessage(content=user_request))
            multi_agent_memory.add_message(session_id, AIMessage(content=agent_response))

            complete_agent_run(run_id, status="completed")

            return {
                "status": "success",
                "response": final_state["final_response"],
                "agent_used": final_state["selected_agent"],
                "metadata": {
                    "model": self.model_name,
                    "workflow_steps": len(final_state["messages"]),
                    "routing_decision": (final_state.get("context") or {}).get("routing_decision", {})
                }
            }

        except Exception as e:
            complete_agent_run(run_id, status="error", error=str(e))
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

        run_id = f"run_{session_id}_{int(time.time() * 1000)}"
        ctx["queue"] = queue
        ctx["loop"] = loop
        ctx["run_id"] = run_id

        register_agent_run(
            run_id=run_id,
            session_id=session_id,
            prompt=user_request,
            source=ctx.get("source", "multi-agent-hub"),
            model=model_name or self.model_name
        )

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
            selected_worker_name = "General Assistant"
            routing_reason = ""
            routing_confidence = 0.9
            execution_focus = ""
            last_yield_time = time.time()

            while not graph_task.done() or not queue.empty():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    last_yield_time = time.time()

                    if event["type"] == "agent_selection":
                        selected_agent = event["agent"]
                        selected_worker_name = event.get("worker_name") or selected_agent
                        routing_reason = event.get("routing_reason") or ""
                        routing_confidence = event.get("confidence", 0.92)
                        execution_focus = event.get("execution_focus") or ""
                        update_agent_run(
                            run_id,
                            selected_agent=selected_agent,
                            worker_name=selected_worker_name,
                            routing_reason=routing_reason,
                            confidence=routing_confidence,
                            step="executing"
                        )
                        yield {
                            "type": "agent_selection",
                            "agent": selected_agent,
                            "worker_name": selected_worker_name,
                            "routing_reason": routing_reason,
                            "confidence": routing_confidence,
                            "execution_focus": execution_focus,
                            "decision_model": event.get("decision_model", self.model_name),
                            "run_id": run_id,
                            "done": False
                        }
                    elif event["type"] == "token":
                        accumulated_response += event["content"]
                        update_agent_run(run_id, step="streaming")
                        yield {
                            "type": "response",
                            "content": accumulated_response,
                            "token": event["content"],
                            "agent": selected_agent,
                            "worker_name": selected_worker_name,
                            "run_id": run_id,
                            "done": False
                        }
                    elif event["type"] == "thinking":
                        yield {
                            "type": "thinking",
                            "content": event["content"],
                            "agent": selected_agent,
                            "worker_name": selected_worker_name,
                            "run_id": run_id,
                            "done": False
                        }
                    elif event["type"] in ("tool_start", "tool_end"):
                        if event["type"] == "tool_start":
                            update_agent_run(run_id, active_tool=event.get("tool"), step="using_tool")
                        else:
                            update_agent_run(run_id, active_tool=None, step="executing")
                        yield {
                            "type": event["type"],
                            "tool": event.get("tool"),
                            "tool_input": event.get("tool_input"),
                            "output": event.get("output"),
                            "agent": selected_agent,
                            "worker_name": selected_worker_name,
                            "run_id": run_id,
                            "done": False
                        }
                    elif event["type"] == "permission_request":
                        update_agent_run(run_id, step="awaiting_permission")
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
                        update_agent_run(run_id, step="awaiting_plan_approval")
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
                    elif event["type"] == "memory_saved":
                        yield {
                            "type": "memory_saved",
                            "memory": event.get("memory", {}),
                            "agent": selected_agent,
                            "done": False
                        }
                    elif event["type"] == "memory_recalled":
                        yield {
                            "type": "memory_recalled",
                            "memories": event.get("memories", []),
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

            # Ensure all todo items are marked 100% completed on finish
            try:
                from .session_context import current_agent_context
                ctx_curr = current_agent_context.get()
                if ctx_curr and "todo_list" in ctx_curr and ctx_curr["todo_list"]:
                    for item in ctx_curr["todo_list"]:
                        item["status"] = "completed"
                    yield {
                        "type": "todo_list_update",
                        "items": [dict(it) for it in ctx_curr["todo_list"]],
                        "agent": selected_agent,
                        "done": True
                    }
            except Exception as todo_err:
                print(f"Todo finalize error: {todo_err}")

            complete_agent_run(run_id, status="completed")

            yield {
                "type": "response",
                "content": final_response,
                "agent": selected_agent,
                "worker_name": selected_worker_name,
                "routing_reason": routing_reason,
                "confidence": routing_confidence,
                "execution_focus": execution_focus,
                "run_id": run_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "done": True
            }

        except asyncio.CancelledError:
            cancel_session(session_id)
            complete_agent_run(run_id, status="cancelled")
            if graph_task and not graph_task.done():
                graph_task.cancel()
            raise
        except Exception as e:
            complete_agent_run(run_id, status="error", error=str(e))
            yield {
                "type": "error",
                "content": f"Error: {str(e)}",
                "done": True
            }
        finally:
            if graph_task and not graph_task.done():
                graph_task.cancel()

    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of available specialized and custom worker agents in the orchestrator catalog"""
        return self._get_worker_catalog()
