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
from .tools import get_tools_for_agent


class RobustReActParser(ReActSingleInputOutputParser):
    """Robust output parser for ReAct agents that recovers from minor formatting issues and infinite loops"""
    
    def parse(self, text: str) -> AgentAction | AgentFinish:
        try:
            return super().parse(text)
        except OutputParserException:
            text_lower = text.lower()
            
            # 1. Fallback for Final Answer in lowercase or mid-thought
            final_answer_marker = "final answer:"
            if final_answer_marker in text_lower:
                idx = text_lower.rfind(final_answer_marker)
                final_ans = text[idx + len(final_answer_marker):].strip()
                return AgentFinish({"output": final_ans}, text)
                
            # 2. Conversational fallback (no tool actions in response)
            if "action:" not in text_lower and "action input:" not in text_lower:
                clean_output = text
                if text_lower.strip().startswith("thought:"):
                    clean_output = text[8:].strip()
                return AgentFinish({"output": clean_output}, text)
                
            # 3. Looser parsing for Action/Action Input
            action_match = re.search(r"action\s*(?:\d+)??\s*:\s*(.+)", text, re.IGNORECASE)
            input_match = re.search(r"action\s*(?:\d+)??\s*input\s*(?:\d+)??\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
            
            if action_match and input_match:
                action = action_match.group(1).split("\n")[0].strip()
                action_input = input_match.group(1).strip()
                action_input = action_input.strip('"').strip("'")
                return AgentAction(action, action_input, text)
                
            # 4. Ultimate fallback to return raw text as final answer to prevent hanging loops
            clean_output = text
            if text_lower.strip().startswith("thought:"):
                clean_output = text[8:].strip()
            return AgentFinish({"output": clean_output}, text)


class ThreadSafeAgentCallbackHandler(BaseCallbackHandler):
    """Callback handler that thread-safely streams tokens and tools to an asyncio.Queue"""
    
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, agent_type: str):
        self.queue = queue
        self.loop = loop
        self.agent_type = agent_type
        self.buffer = ""
        self.final_answer_started = False
        
    def _put_event(self, event: dict):
        self.loop.call_soon_threadsafe(self.queue.put_nowait, event)
        
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        if self.agent_type == "general":
            # Stream directly for the general conversational agent
            self._put_event({"type": "token", "content": token})
        else:
            # For tool-using agents, buffer tokens but stream them as 'thinking' events
            # so the user can see progress. Once "Final Answer:" is detected, switch
            # to streaming as 'token' events for the final output.
            if self.final_answer_started:
                self._put_event({"type": "token", "content": token})
            else:
                self.buffer += token
                # Emit thinking event so the UI can show agent reasoning in real-time
                self._put_event({"type": "thinking", "content": token})
                
                # Check for "final answer:", "final response:", "answer:", etc. case-insensitively using regex
                buffer_lower = self.buffer.lower()
                match = re.search(r'(final answer|final response|answer):\s*', buffer_lower)
                if match:
                    idx = match.start()
                    after_final = self.buffer[idx + len(match.group(0)):].lstrip()
                    if after_final:
                        self._put_event({"type": "token", "content": after_final})
                    self.final_answer_started = True
                    
    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        self._put_event({
            "type": "tool_start",
            "tool": action.tool,
            "tool_input": action.tool_input
        })
        
    def on_tool_end(self, output: str, **kwargs) -> None:
        self._put_event({
            "type": "tool_end",
            "output": output
        })
        
    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        if not self.final_answer_started and self.agent_type != "general":
            # Send final output if Final Answer wasn't seen in tokens
            self._put_event({"type": "token", "content": finish.return_values.get("output", "")})
            self.final_answer_started = True


def get_workspace_instructions() -> str:
    """Dynamically get workspace instructions based on configuration whitelist"""
    from .config_store import get_allowed_paths
    from .config import AGENT_WORKSPACE_DIR
    
    allowed = get_allowed_paths()
    if allowed:
        paths_str = "\n".join(f"- {p}" for p in allowed)
        return f"""RESTRICTED ACCESS PATHS:
You are configured to only have access to specific directories/files.
You CAN ONLY read and write to these paths:
{paths_str}

Use absolute paths when targeting these locations. Any attempt to write or read outside these locations will be denied by the security sandbox."""
    else:
        return f"WORKSPACE: {AGENT_WORKSPACE_DIR}"


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
        self.name = name
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.ollama_base_url = ollama_base_url
        
        # Initialize LLM with streaming enabled and lower temperature to prevent hallucination
        self.llm = SafeChatOllama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=0.1,  # Lower temperature for strict formatting compliance and less hallucination
            timeout=300,
            streaming=True,
            stop=["\nQuestion:", "Question:"]
        )
        
        # Get specialized tools
        if custom_tools is not None:
            from .tools import get_tools_by_names
            self.tools = get_tools_by_names(custom_tools)
        else:
            self.tools = get_tools_for_agent(agent_type)
            
        # Load MCP tools if configured
        if mcp_servers:
            from .mcp_client import mcp_manager
            mcp_tools = mcp_manager.get_tools_for_agent_sync(mcp_servers)
            self.tools.extend(mcp_tools)
        
        # Escape curly braces in system prompt so PromptTemplate doesn't treat them as variables
        escaped_system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")
        
        # Create agent with tools and the RobustReActParser
        prompt = PromptTemplate.from_template(
            f"""{escaped_system_prompt}

You have access to the following tools:

{{tools}}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question. You MUST always provide a detailed, helpful walkthrough and summary of what you did, what files were created or modified, and how the user can check or run the results. Never just output a single character or empty response.

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
            max_iterations=20,  # Increased for complex tasks
            max_execution_time=300  # 5 minutes timeout
        )
        
    def process(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[BaseMessage]] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ) -> str:
        """Process a task and return the result"""
        import time
        from .session_context import current_agent_context, current_token_usage
        
        start_time = time.time()
        token = None
        token_usage_var = None
        
        # Initialize token usage tracking dictionary in context
        usage_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        token_usage_var = current_token_usage.set(usage_info)
        
        try:
            # Set context variables for tools to access
            if context and "queue" in context and "loop" in context:
                token = current_agent_context.set({
                    "session_id": context.get("session_id", "default"),
                    "queue": context["queue"],
                    "loop": context["loop"]
                })

            # Add context to task if provided
            if context:
                # Remove loop and queue from printed context to keep prompt clean
                clean_context = {k: v for k, v in context.items() if k not in ["queue", "loop"]}
                if clean_context:
                    task = f"{task}\n\nContext: {clean_context}"
            
            # Format chat history
            formatted_history = ""
            if chat_history:
                formatted = []
                for msg in chat_history:
                    role = "User" if msg.type == "human" else "Assistant"
                    formatted.append(f"{role}: {msg.content}")
                formatted_history = "\n".join(formatted)
            
            # Execute agent with tools
            result = self.agent_executor.invoke(
                {
                    "input": task,
                    "chat_history": formatted_history
                },
                config={"callbacks": callbacks} if callbacks else None
            )
            
            # Handle different result types
            output_text = ""
            if isinstance(result, dict):
                output_text = result.get("output", str(result))
            elif isinstance(result, str):
                output_text = result
            else:
                output_text = str(result)
                
            return output_text
            
        except Exception as e:
            return f"Error processing task: {str(e)}"
        finally:
            # Reset agent context
            if token is not None:
                current_agent_context.reset(token)
                
            # Capture usage info and reset token usage context
            if token_usage_var is not None:
                usage_info = current_token_usage.get()
                current_token_usage.reset(token_usage_var)
                
                # Log performance and token usage to database
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
                    
                    # Update token count of the last chat message in the session if provided
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
        """Return agent capabilities"""
        return {
            "name": self.name,
            "type": self.agent_type,
            "tools": [tool.name for tool in self.tools],
            "description": self.system_prompt[:200]
        }


class CodeAgent(BaseSpecializedAgent):
    """Agent specialized in code generation and execution"""
    
    def __init__(self, model_name: str = DEFAULT_CODE_MODEL, ollama_base_url: str = "http://localhost:11434"):
        
        system_prompt = f"""You are a Code Agent. You MUST use tools to create and fix files!

{get_workspace_instructions()}

CRITICAL RULES:
1. When asked to create files, CALL the file_operation tool with operation "write".
2. When asked to fix or update a file, FIRST read it with operation "read", then write the corrected version with operation "write".
3. DO NOT just describe - ACTUALLY CREATE or FIX files using tools.
4. ALWAYS use Action/Action Input format.
5. Code MUST be formatted with proper indentation and newlines. Never write all code in one line.
6. In your Final Answer, you MUST always write a detailed walkthrough of what you did, which files you created or modified, and explain how the user can open, test, or run the application. Never just say "-" or give an empty answer.

Tools YOU MUST USE:
1. file_operation - READ, WRITE, or LIST files
   To READ a file:  {{"operation": "read", "path": "filename.py"}}
   To WRITE a file: {{"operation": "write", "path": "filename.py", "content": "file content here"}}
   To LIST files:   {{"operation": "list", "path": ""}}

2. create_project - For multiple files
   Input: dict with file paths as keys and content as values

WORKFLOW FOR CREATING NEW FILES:
Step 1: Generate complete code with correct indentation and newlines
Step 2: CALL file_operation tool with operation "write" and the formatted code
Step 3: Confirm creation

WORKFLOW FOR FIXING EXISTING FILES:
Step 1: CALL file_operation with operation "read" to read the existing file
Step 2: Analyze the code and identify the errors/issues
Step 3: Generate the COMPLETE corrected code (not just the changed parts)
Step 4: CALL file_operation with operation "write" to overwrite the file with the fixed version
Step 5: Confirm the fix was applied

Example for reading and fixing a file:
Action: file_operation
Action Input: {{"operation": "read", "path": "app.py"}}
(After reading, fix errors and write back)
Action: file_operation
Action Input: {{"operation": "write", "path": "app.py", "content": "def calculate_factorial(n):\\n    if n == 0 or n == 1:\\n        return 1\\n    return n * calculate_factorial(n - 1)\\n\\nif __name__ == '__main__':\\n    print(calculate_factorial(5))"}}

3. execute_terminal - Run terminal/shell commands
   Input: {{"command": "npm install", "cwd": "/path/to/dir"}}
   The user will be asked to approve the command before execution.
   Use this to run apps, install packages, run scripts, etc.

4. schedule_task - Schedule a future or recurring agent task
   Input: {{"task_name": "Check Nike shoes", "prompt": "Search the web for Nike Mind shoes availability and report the result", "interval_minutes": 60, "delay_minutes": 1}}
   For one-time tasks, set interval_minutes to 0.
   For recurring loops, set interval_minutes to the desired repeat interval.

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

IMPORTANT STEPS:
1. First, READ the file using: Action: file_operation with {{"operation": "read", "path": "{filepath}"}}
2. Then analyze the code and apply ALL the fixes from the analysis report
3. Write the COMPLETE corrected file back using: Action: file_operation with {{"operation": "write", "path": "{filepath}", "content": "...fixed code..."}}
4. Confirm what was fixed

Do NOT skip any step. You MUST read the file first, then write the corrected version."""

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
- Summarize complex documents and articles
- Compare and contrast different approaches
- Provide well-researched recommendations
- Stay up-to-date with latest trends and technologies

When given a research task:
1. Break down the research question
2. Gather relevant information
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
        
        system_prompt = f"""You are an Analysis Agent specialized in code and data analysis.

{get_workspace_instructions()}

Your capabilities:
- Read and analyze files from the workspace
- Analyze code quality and performance
- Identify bugs, errors, and security vulnerabilities
- Suggest optimizations and improvements
- Review code architecture and design patterns
- Produce structured analysis reports with specific fix instructions

CRITICAL: When asked to analyze a file from the workspace:
1. FIRST use file_operation with operation "read" to read the file content
2. Then use analyze_code to perform analysis
3. Provide a structured report with specific, actionable fixes

To read a file:
Action: file_operation
Action Input: {{"operation": "read", "path": "filename.py"}}

To list workspace files:
Action: file_operation
Action Input: {{"operation": "list", "path": ""}}

When providing analysis, structure your output as:
- ERRORS FOUND: List each error with line number and description
- FIXES REQUIRED: For each error, describe the exact fix needed
- IMPROVED CODE: Provide the corrected version of problematic sections

Always provide detailed, constructive, and actionable analysis."""

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
            "type": "file_analysis",
            "filepath": filepath
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
}


def create_specialized_agent(
    agent_type: str,
    model_name: Optional[str] = None,
    ollama_base_url: str = "http://localhost:11434"
) -> Optional[BaseSpecializedAgent]:
    """Create a specialized agent by type"""
    if model_name is None:
        model_name = DEFAULT_CODE_MODEL if agent_type == "code" else DEFAULT_MAIN_MODEL
        
    if agent_type in SPECIALIZED_AGENTS:
        return SPECIALIZED_AGENTS[agent_type](model_name, ollama_base_url)
        
    # Load custom agent from DB
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

# Made with Bob
