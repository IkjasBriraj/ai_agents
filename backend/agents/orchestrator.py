"""
Orchestrator Agent
Main agent that coordinates specialized agents using LangGraph
"""

import asyncio
from typing import Dict, Any, List, Optional, TypedDict, Annotated
import operator
from .specialized_agents import SafeChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from .specialized_agents import create_specialized_agent, SPECIALIZED_AGENTS
from .memory import multi_agent_memory
from .config import DEFAULT_MAIN_MODEL, DEFAULT_CODE_MODEL


class AgentState(TypedDict):
    """State for the agent graph"""
    messages: Annotated[List[BaseMessage], operator.add]
    user_request: str
    selected_agent: Optional[str]
    agent_response: Optional[str]
    final_response: Optional[str]
    context: Dict[str, Any]
    session_id: str


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
            temperature=0.3,  # Lower temperature for more consistent routing
            timeout=300
        )
        
        # System prompt for orchestrator
        self.system_prompt = """You are the Orchestrator Agent, responsible for routing user requests to specialized agents.

Available specialized agents:
1. CODE AGENT - For software development tasks:
   - Generate code in any programming language
   - Create complete applications
   - Execute and test code
   - File operations (read/write)
   - Run terminal/shell commands (npm, python, pip, etc.)
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

4. ANALYZE AND FIX - For requests that need BOTH analysis AND fixing:
   - When user wants to analyze a file AND fix the errors
   - When user says "fix errors", "debug this file", "find and fix bugs"
   - The Analysis Agent will first analyze, then the Code Agent will fix

Your job:
1. Analyze the user's request
2. Determine which specialized agent is best suited
3. Route the request to that agent
4. Return the agent's response to the user

IMPORTANT ROUTING RULES:
- If the user asks to "analyze AND fix", "find and fix errors", "debug and fix", "fix the errors in", "fix bugs in" -> respond with "analyze_and_fix"
- If the user asks to only analyze or review code (no fixing) -> respond with "analysis"
- If the user asks to create, generate, or write new code -> respond with "code"
- If the user asks to fix or update an existing file -> respond with "code"
- If the user asks to run a command, run an app, start a server, install packages, or execute terminal commands -> respond with "code"
- If the user asks to schedule a task, set a timer, check something periodically, or create a loop -> respond with "code"

Respond with ONLY the agent name: "code", "research", "analysis", "analyze_and_fix"
If the request is general or conversational, respond with "general"."""

        # Build the LangGraph workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("route_to_agent", self._route_to_agent)
        workflow.add_node("generate_response", self._generate_response)
        
        # Define edges
        workflow.set_entry_point("analyze_request")
        workflow.add_edge("analyze_request", "route_to_agent")
        workflow.add_edge("route_to_agent", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _analyze_request(self, state: AgentState) -> AgentState:
        """Analyze the user request and determine which agent to use"""
        user_request = state["user_request"]
        session_id = state.get("session_id", "default")
        
        # Quick keyword-based pre-check for analyze_and_fix patterns
        request_lower = user_request.lower()
        fix_keywords = [
            "fix error", "fix bug", "fix the error", "fix the bug", "debug and fix",
            "find and fix", "analyze and fix", "fix issues in", "fix this file",
            "fix errors in", "fix bugs in", "correct the errors", "fix issue in",
            "fix the issue in", "getting this error", "getting an error", "got this error",
            "error is", "solve the error", "resolve the error", "fix it"
        ]
        
        is_fix_request = any(kw in request_lower for kw in fix_keywords)
        
        # Quick keyword-based pre-check for terminal/run/schedule patterns
        terminal_keywords = [
            "run the app", "run my app", "run this app", "start the server",
            "npm run", "npm start", "npm install", "pip install", "python run",
            "run the command", "execute command", "run command", "terminal",
            "start the app", "launch the app", "run it"
        ]
        schedule_keywords = [
            "schedule", "every day", "every hour", "every minute", "periodically",
            "check every", "loop", "timer", "remind me", "tomorrow morning",
            "in the morning", "recurring", "repeat every"
        ]
        
        is_terminal_request = any(kw in request_lower for kw in terminal_keywords)
        is_schedule_request = any(kw in request_lower for kw in schedule_keywords)
        
        if is_fix_request:
            selected_agent = "analyze_and_fix"
        elif is_terminal_request or is_schedule_request:
            selected_agent = "code"
        else:
            # Format and inject history for routing context
            history_str = multi_agent_memory.format_history(session_id)
            history_prompt = ""
            if history_str:
                history_prompt = f"\n\nConversation History:\n{history_str}"
            
            # Build prompt for agent selection
            messages = [
                SystemMessage(content=self.system_prompt + history_prompt),
                HumanMessage(content=f"User request: {user_request}\n\nWhich agent should handle this? Respond with ONLY ONE of: code, research, analysis, analyze_and_fix, general")
            ]
            
            # Get LLM response
            response = self.llm.invoke(messages)
            selected_agent = response.content.strip().lower()
            
            # Clean up the response - extract just the agent name
            for valid_agent in ["analyze_and_fix", "code", "research", "analysis", "general"]:
                if valid_agent in selected_agent:
                    selected_agent = valid_agent
                    break
            else:
                selected_agent = "general"
        
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
    
    def _route_to_agent(self, state: AgentState) -> AgentState:
        """Route the request to the selected specialized agent"""
        selected_agent = state["selected_agent"]
        user_request = state["user_request"]
        session_id = state.get("session_id", "default")
        
        # Get queue and loop if streaming is active
        callbacks = []
        context = dict(state.get("context") or {})
        context["session_id"] = session_id
        if "queue" in context and "loop" in context:
            from .specialized_agents import ThreadSafeAgentCallbackHandler
            cb = ThreadSafeAgentCallbackHandler(context["queue"], context["loop"], selected_agent)
            callbacks.append(cb)
        
        if selected_agent == "general":
            # Handle general requests directly
            history = multi_agent_memory.get_messages(session_id)
            messages = [
                SystemMessage(content="You are a helpful AI assistant.")
            ]
            messages.extend(history)
            messages.append(HumanMessage(content=user_request))
            response = self.llm.invoke(messages, config={"callbacks": callbacks} if callbacks else None)
            state["agent_response"] = response.content
        elif selected_agent == "analyze_and_fix":
            # CHAINED WORKFLOW: Analysis Agent → Code Agent
            state["agent_response"] = self._analyze_and_fix(user_request, context, session_id=session_id, callbacks=callbacks)
        else:
            # Create and use specialized agent
            agent_model = DEFAULT_CODE_MODEL if selected_agent == "code" else self.model_name
            agent = create_specialized_agent(
                selected_agent,
                agent_model,
                self.ollama_base_url
            )
            
            if agent:
                # Process the request with the specialized agent
                chat_history = multi_agent_memory.get_messages(session_id)
                result = agent.process(user_request, context, chat_history=chat_history, callbacks=callbacks)
                state["agent_response"] = result
            else:
                state["agent_response"] = f"Error: Could not create {selected_agent} agent"
        
        return state
    
    def _analyze_and_fix(self, user_request: str, context: dict = None, session_id: str = "default", callbacks: Optional[List[Any]] = None) -> str:
        """Chain Analysis Agent → Code Agent for analyze-and-fix workflows"""
        import re
        from langchain_core.messages import AIMessage
        
        # Get chat history for scanning and processing
        chat_history = multi_agent_memory.get_messages(session_id)
        
        # Extract filename from user request if mentioned
        filepath = None
        # Match patterns like "fix errors in app.py", "analyze calculator.py", etc., supporting directories and drive letters
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
                
        # If filepath not found in the current request, scan history backwards to find the last created/modified file
        if not filepath and chat_history:
            for msg in reversed(chat_history):
                if isinstance(msg, AIMessage):
                    # Search for [SUCCESS] Created: <path> or Full path: <path>
                    match = re.search(r'\[SUCCESS\] Created:\s*([a-zA-Z0-9_\-\.\/\\\\]+\.[a-zA-Z0-9]+)', msg.content)
                    if match:
                        filepath = match.group(1)
                        break
                    # Search for any wrote/updated/created file indicators in the AI response
                    match_quote = re.search(r'(?:created|wrote|updated|in)\s+["\'`]?([a-zA-Z0-9_\-\.\/\\\\]+\.[a-zA-Z0-9]+)["\'`]?', msg.content, re.IGNORECASE)
                    if match_quote:
                        filepath = match_quote.group(1)
                        break
        
        # Step 1: Analysis Agent reads and analyzes the file/code
        analysis_agent = create_specialized_agent("analysis", self.model_name, self.ollama_base_url)
        if not analysis_agent:
            return "Error: Could not create Analysis Agent"
        
        if filepath:
            analysis_result = analysis_agent.analyze_file(filepath, context=context, chat_history=chat_history, callbacks=callbacks)
        else:
            analysis_result = {"result": analysis_agent.process(user_request, context, chat_history=chat_history, callbacks=callbacks)}
        
        analysis_text = analysis_result.get("result", str(analysis_result))
        
        # Step 2: Code Agent reads the file and applies fixes
        code_agent = create_specialized_agent("code", DEFAULT_CODE_MODEL, self.ollama_base_url)
        if not code_agent:
            return f"**Analysis Complete (but Code Agent unavailable):**\n\n{analysis_text}"
        
        if filepath:
            fix_result = code_agent.fix_file(filepath, analysis_text, context=context, chat_history=chat_history, callbacks=callbacks)
        else:
            fix_task = f"""Based on this analysis, fix the code:\n\n{analysis_text}\n\nOriginal request: {user_request}"""
            fix_result = {"result": code_agent.process(fix_task, context, chat_history=chat_history, callbacks=callbacks)}
        
        fix_text = fix_result.get("result", str(fix_result))
        
        # Combine both reports
        combined = f"""## 🔍 Analysis Report (Analysis Agent)
 
{analysis_text}
 
---
 
## 🔧 Fix Report (Code Agent)
 
{fix_text}"""
        
        return combined
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate the final response to the user"""
        selected_agent = state["selected_agent"]
        agent_response = state["agent_response"]
        
        # Format the final response
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
        """
        Process a user request through the orchestrator
        
        Args:
            user_request: The user's request/prompt
            context: Optional context information
            session_id: The session ID for conversation history
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Initialize state
            initial_state: AgentState = {
                "messages": [HumanMessage(content=user_request)],
                "user_request": user_request,
                "selected_agent": None,
                "agent_response": None,
                "final_response": None,
                "context": context or {},
                "session_id": session_id
            }
            
            # Run the workflow
            final_state = self.workflow.invoke(initial_state)
            
            # Save messages to memory
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
        """
        Process a user request with streaming response
        
        Args:
            user_request: The user's request/prompt
            context: Optional context information
            session_id: The session ID for conversation history
            
        Yields:
            Chunks of the response
        """
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        
        ctx = dict(context or {})
        ctx["queue"] = queue
        ctx["loop"] = loop
        
        try:
            # Initialize state
            initial_state: AgentState = {
                "messages": [HumanMessage(content=user_request)],
                "user_request": user_request,
                "selected_agent": None,
                "agent_response": None,
                "final_response": None,
                "context": ctx,
                "session_id": session_id
            }
            
            # Start the graph execution task in a background thread to avoid blocking the event loop
            graph_task = asyncio.create_task(asyncio.to_thread(self.workflow.invoke, initial_state))
            
            accumulated_response = ""
            selected_agent = "general"
            
            # Stream the events from queue
            while not graph_task.done() or not queue.empty():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.05)
                    
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
                    elif event["type"] == "terminal_output":
                        yield {
                            "type": "terminal_output",
                            "content": event.get("content"),
                            "done": event.get("done", False)
                        }
                        
                    queue.task_done()
                except asyncio.TimeoutError:
                    continue
            
            # Wait for graph execution to finish completely and fetch result
            final_state = await graph_task
            final_response = final_state.get("final_response") or accumulated_response
            selected_agent = final_state.get("selected_agent") or selected_agent
            
            # Save to memory on successful stream completion
            agent_response = final_state.get("agent_response") or accumulated_response or ""
            multi_agent_memory.add_message(session_id, HumanMessage(content=user_request))
            multi_agent_memory.add_message(session_id, AIMessage(content=agent_response))
            
            # Query token counts from the latest performance log for this agent
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
            
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Error: {str(e)}",
                "done": True
            }
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of available specialized agents"""
        agents = []
        for agent_type, agent_class in SPECIALIZED_AGENTS.items():
            agent = agent_class(self.model_name, self.ollama_base_url)
            agents.append(agent.get_capabilities())
        return agents

# Made with Bob
