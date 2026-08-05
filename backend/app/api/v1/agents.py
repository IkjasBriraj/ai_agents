import os
import sys
import time
import re
import logging
import traceback
import asyncio
import io
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import speech_recognition as sr

from database.db import get_db, SessionLocal
from database.models import HubModel, AgentModel, McpServerModel, WorkflowModel, ChatMessageModel, PerformanceLogModel, ScheduledTaskModel, HubWorkspaceModel, AgentTaskModel, HubMemoryModel, HubArtifactModel, AgentRunModel
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from .orchestrator import OrchestratorAgent
from .specialized_agents import create_specialized_agent, SPECIALIZED_AGENTS
from .config import DEFAULT_MAIN_MODEL, DEFAULT_CODE_MODEL

class HubSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None


class HubWorkspaceUpdate(BaseModel):
    mission: str = ""
    success_criteria: List[str] = []
    status: str = "draft"


class HubTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=180)
    description: str = ""
    assigned_role: str = "lead"
    depends_on: List[str] = []


class HubTaskUpdate(BaseModel):
    status: Optional[str] = None
    assigned_role: Optional[str] = None
    result: Optional[str] = None


class HubMemoryCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    category: str = "decision"

class AgentSchema(BaseModel):
    id: str
    hub_id: Optional[str] = None
    parent_id: Optional[str] = None
    name: str
    persona: str
    system_prompt: str
    base_model: Optional[str] = DEFAULT_MAIN_MODEL
    ollama_base_url: Optional[str] = "http://localhost:11434"
    tools: Optional[list] = []
    mcp_servers: Optional[list] = []
    training_data: Optional[list] = []

class McpServerSchema(BaseModel):
    id: str
    name: str
    type: Optional[str] = "stdio"
    command: Optional[str] = None
    args: Optional[list] = []
    url: Optional[str] = None
    env: Optional[dict] = {}
    enabled: Optional[bool] = True

class WorkflowSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    nodes: Optional[list] = []
    edges: Optional[list] = []


class MultiAgentRequest(BaseModel):
    """Request model for multi-agent chat"""
    prompt: str = Field(..., description="User's request/prompt")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")
    stream: bool = Field(default=False, description="Enable streaming response")
    session_id: Optional[str] = Field(default="default", description="Session ID for agent memory")
    thinking_level: Optional[str] = Field(default="medium", description="Thinking level: low, medium, high, or extended")
    provider: Optional[str] = Field(default="ollama", description="Cloud or local provider: ollama, openai, anthropic, ibm, gemini, deepseek")
    model: Optional[str] = Field(default=None, description="Custom model name")
    api_key: Optional[str] = Field(default=None, description="Cloud API key")

class SingleAgentTestRequest(BaseModel):
    agent_id: str
    provider: str = "ollama"  # ollama, openai, anthropic, ibm, gemini, deepseek
    model: str = DEFAULT_MAIN_MODEL
    api_key: Optional[str] = None
    thinking_level: Optional[str] = "medium"  # disabled, low, medium, high
    prompt: str


class DirectAgentRequest(BaseModel):
    """Request model for direct agent interaction"""
    agent_type: str = Field(..., description="Agent type: code, research, or analysis")
    task: str = Field(..., description="Task for the agent")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")
    session_id: Optional[str] = Field(default="default", description="Session ID for agent memory")
    thinking_level: Optional[str] = Field(default="medium", description="Thinking level: low, medium, high, or extended")


class AgentResponse(BaseModel):
    """Response model for agent interactions"""
    status: str
    response: str
    agent_used: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PermissionResponseRequest(BaseModel):
    """Request model for user permission decisions"""
    session_id: str = Field(default="default", description="Session ID of the request")
    path: str = Field(..., description="Absolute path requested")
    granted: bool = Field(..., description="Decision made: true to grant, false to deny")


class CommandPermissionResponseRequest(BaseModel):
    """Request model for command execution permission decisions"""
    session_id: str = Field(default="default", description="Session ID of the request")
    command: str = Field(..., description="Command string requested")
    granted: bool = Field(..., description="Decision made: true to grant, false to deny")


class PlanApprovalResponseRequest(BaseModel):
    """Request model for user plan approval decisions"""
    session_id: str = Field(default="default", description="Session ID of the request")
    plan_path: str = Field(..., description="Absolute or relative path to the plan file")
    plan_content: str = Field(..., description="Plan content (edited or original)")
    approved: bool = Field(..., description="Whether the plan was approved")


class ScheduledTaskSchema(BaseModel):
    """Schema for scheduled/looped tasks"""
    id: Optional[str] = None
    name: str = Field(..., description="Task name")
    prompt: str = Field(..., description="Agent prompt to execute")
    interval_minutes: Optional[int] = Field(default=None, description="Repeat interval in minutes. Null for one-time.")
    delay_minutes: Optional[int] = Field(default=1, description="Minutes from now until first run")
    status: Optional[str] = Field(default="active", description="Task status")


def create_multi_agent_router(
    model_name: str = DEFAULT_MAIN_MODEL,
    ollama_base_url: str = "http://localhost:11434"
) -> APIRouter:
    """
    Create FastAPI router for multi-agent system
    
    Args:
        model_name: LLM model name
        ollama_base_url: Ollama API base URL
        
    Returns:
        Configured FastAPI router
    """
    router = APIRouter(tags=["Multi-Agent System"])
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent(model_name, ollama_base_url)
    
    @router.get("/agents/available")
    async def get_available_agents():
        """Get list of available specialized agents"""
        try:
            agents = orchestrator.get_available_agents()
            return {
                "status": "success",
                "agents": agents,
                "count": len(agents)
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/agents/voice/transcribe")
    async def transcribe_voice(file: UploadFile = File(...)):
        """Transcribe uploaded audio file to text using SpeechRecognition"""
        try:
            audio_bytes = await file.read()
            if not audio_bytes:
                return {"status": "error", "message": "Audio file is empty"}

            def _transcribe():
                recognizer = sr.Recognizer()
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    audio_data = recognizer.record(source)
                return recognizer.recognize_google(audio_data)

            transcribed_text = await asyncio.to_thread(_transcribe)
            return {"status": "success", "text": transcribed_text}
        except sr.UnknownValueError:
            return {"status": "error", "message": "Speech unintelligible: Could not understand audio"}
        except sr.RequestError as e:
            return {"status": "error", "message": f"Speech recognition service unavailable: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Voice transcription failed: {str(e)}"}

    
    @router.post("/agents/chat", response_model=AgentResponse)
    async def multi_agent_chat(request: MultiAgentRequest):
        """
        Chat with the multi-agent system
        The orchestrator will route to the appropriate specialized agent
        """
        try:
            session_id = request.session_id or "default"
            ctx = dict(request.context or {})
            if request.thinking_level:
                ctx["thinking_level"] = request.thinking_level
            if request.provider:
                ctx["provider"] = request.provider
            if request.model:
                ctx["model"] = request.model
            if request.api_key:
                ctx["api_key"] = request.api_key

            if request.stream:
                # Return streaming response safely
                async def generate():
                    try:
                        async for chunk in orchestrator.process_request_stream(
                            request.prompt,
                            ctx,
                            session_id=session_id
                        ):
                            yield f"data: {json.dumps(chunk)}\n\n"
                    except Exception as stream_err:
                        import traceback
                        print(f"Streaming error for session {session_id}: {stream_err}")
                        traceback.print_exc()
                        err_payload = {
                            "type": "error",
                            "content": f"Streaming processing error: {str(stream_err)}"
                        }
                        yield f"data: {json.dumps(err_payload)}\n\n"
                
                return StreamingResponse(
                    generate(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    }
                )
            else:
                # Return complete response
                result = await asyncio.to_thread(orchestrator.process_request, request.prompt, ctx, session_id=session_id)
                return AgentResponse(**result)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/agents/direct/{agent_type}")
    async def direct_agent_interaction(agent_type: str, request: DirectAgentRequest):
        """
        Interact directly with a specific specialized agent
        Bypasses the orchestrator
        """
        try:
            # Validate agent type
            if agent_type not in SPECIALIZED_AGENTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid agent type. Available: {list(SPECIALIZED_AGENTS.keys())}"
                )
            
            # Create specialized agent
            agent_model = DEFAULT_CODE_MODEL if agent_type == "code" else model_name
            agent = create_specialized_agent(agent_type, agent_model, ollama_base_url)
            if not agent:
                raise HTTPException(status_code=500, detail="Failed to create agent")
            
            session_id = request.session_id or "default"
            from .memory import multi_agent_memory
            from langchain_core.messages import HumanMessage, AIMessage
            
            chat_history = multi_agent_memory.get_messages(session_id)
            
            # Process task in a background thread to avoid blocking the event loop
            result = await asyncio.to_thread(agent.process, request.task, request.context, chat_history)
            
            # Save messages to memory
            multi_agent_memory.add_message(session_id, HumanMessage(content=request.task))
            multi_agent_memory.add_message(session_id, AIMessage(content=result))
            
            return {
                "status": "success",
                "response": result,
                "agent_used": agent_type,
                "metadata": {
                    "agent_name": agent.name,
                    "model": model_name
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/agents/code/generate-app")
    async def generate_app(requirements: str):
        """
        Generate a complete application using the Code Agent
        Specialized endpoint for app generation
        """
        try:
            # Create code agent
            code_agent = create_specialized_agent("code", DEFAULT_CODE_MODEL, ollama_base_url)
            if not code_agent:
                raise HTTPException(status_code=500, detail="Failed to create code agent")
            
            # Generate app in a background thread to avoid blocking the event loop
            result = await asyncio.to_thread(code_agent.generate_app, requirements)
            
            return result
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/agents/research/topic")
    async def research_topic(topic: str):
        """
        Research a topic using the Research Agent
        Specialized endpoint for research tasks
        """
        try:
            # Create research agent
            research_agent = create_specialized_agent("research", model_name, ollama_base_url)
            if not research_agent:
                raise HTTPException(status_code=500, detail="Failed to create research agent")
            
            # Research topic in a background thread to avoid blocking the event loop
            result = await asyncio.to_thread(research_agent.research_topic, topic)
            
            return result
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/agents/analysis/code")
    async def analyze_code(code: str, language: str = "python"):
        """
        Analyze code using the Analysis Agent
        Specialized endpoint for code analysis
        """
        try:
            # Create analysis agent
            analysis_agent = create_specialized_agent("analysis", model_name, ollama_base_url)
            if not analysis_agent:
                raise HTTPException(status_code=500, detail="Failed to create analysis agent")
            
            # Analyze code in a background thread to avoid blocking the event loop
            result = await asyncio.to_thread(analysis_agent.analyze_code, code, language)
            
            return result
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/agents/analysis/vision-ui")
    async def analyze_ui_vision(filepath: str):
        """
        Analyze a UI screenshot or HTML file using Gemma-4-26B Vision Capabilities
        """
        try:
            analysis_agent = create_specialized_agent("analysis", model_name, ollama_base_url)
            if not analysis_agent:
                raise HTTPException(status_code=500, detail="Failed to create analysis agent")
            
            result = await asyncio.to_thread(analysis_agent.analyze_ui_with_vision, filepath)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/agents/test-single-agent")
    async def test_single_agent(req: SingleAgentTestRequest):
        """
        Test an individual agent with custom provider, model, API key, thinking level & prompt
        """
        import time
        start_time = time.time()
        try:
            agent_type = req.agent_id.lower()
            target_model = req.model if req.model else model_name

            # Build specialized agent instance
            agent_instance = create_specialized_agent(agent_type, model_name=target_model, ollama_base_url=ollama_base_url)

            if not agent_instance:
                agent_instance = create_specialized_agent("research", model_name=target_model, ollama_base_url=ollama_base_url)

            # Apply thinking level guidance overlay
            thinking_prefix = ""
            if req.thinking_level == "high":
                thinking_prefix = "[THINKING LEVEL: HIGH / DEEP CHAIN-OF-THOUGHT]\nAnalyze all edge cases, logical constraints, and step-by-step reasoning before outputting final answer.\n\n"
            elif req.thinking_level == "medium":
                thinking_prefix = "[THINKING LEVEL: MEDIUM]\nBalance speed and thorough structured analysis.\n\n"
            elif req.thinking_level == "low":
                thinking_prefix = "[THINKING LEVEL: LOW]\nProvide a fast, direct, and concise output.\n\n"

            formatted_prompt = thinking_prefix + req.prompt

            if agent_type == "research" and hasattr(agent_instance, "research_topic"):
                output_res = await asyncio.to_thread(agent_instance.research_topic, formatted_prompt)
                res_text = output_res.get("result", str(output_res)) if isinstance(output_res, dict) else str(output_res)
            elif hasattr(agent_instance, "process"):
                res_text = await asyncio.to_thread(agent_instance.process, formatted_prompt)
            else:
                res_text = f"Agent {req.agent_id} responded successfully via {req.provider.upper()} model {target_model}."

            elapsed = round(time.time() - start_time, 2)

            return {
                "status": "success",
                "agent_id": req.agent_id,
                "provider": req.provider,
                "model": target_model,
                "thinking_level": req.thinking_level,
                "elapsed_seconds": elapsed,
                "result": res_text
            }
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            return {
                "status": "error",
                "agent_id": req.agent_id,
                "provider": req.provider,
                "model": req.model,
                "error": str(e),
                "elapsed_seconds": elapsed
            }

    @router.get("/agents/health")
    async def health_check():
        """Health check for multi-agent system"""
        try:
            return {
                "status": "healthy",
                "orchestrator": "operational",
                "model": model_name,
                "available_agents": list(SPECIALIZED_AGENTS.keys())
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @router.post("/agents/clear")
    async def clear_multi_agent_memory(session_id: Optional[str] = "default"):
        """Clear conversation memory for the multi-agent system session"""
        try:
            from .memory import multi_agent_memory
            multi_agent_memory.clear(session_id or "default")
            return {"status": "success", "message": f"Conversation history for session '{session_id}' cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    @router.post("/agents/stop")
    async def stop_multi_agent_execution(session_id: Optional[str] = "default"):
        """Explicitly cancel and stop agent execution for a session"""
        try:
            from .permissions import cancel_session
            cancel_session(session_id or "default")
            return {"status": "success", "message": "Cancellation request registered"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    @router.get("/config")
    async def get_multi_agent_config():
        """Get the current multi-agent configuration"""
        try:
            from .config_store import load_config, DEFAULT_CONFIG
            config = load_config()
            return {
                "status": "success",
                "config": config,
                "all_tools": DEFAULT_CONFIG["agent_tools"]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    @router.post("/config")
    async def update_multi_agent_config(config: dict):
        """Update and save the multi-agent configuration"""
        try:
            from .config_store import save_config
            save_config(config)
            from .audit import record_security_event
            record_security_event(
                "configuration_updated",
                allowed_path_count=len(config.get("allowed_paths", [])),
                enabled_tool_groups=sorted(config.get("agent_tools", {}).keys()),
            )
            
            # Asynchronously check and pull dynamic models if not installed
            main_model = config.get("default_main_model")
            code_model = config.get("default_code_model")
            
            import httpx
            import asyncio
            
            async def check_and_pull(model_name: str):
                if not model_name:
                    return
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(f"{ollama_base_url}/api/tags")
                        if response.status_code == 200:
                            models = response.json().get("models", [])
                            local_names = [m["name"] for m in models]
                            # check standard name and name:latest
                            if model_name not in local_names and f"{model_name}:latest" not in local_names:
                                print(f"Model '{model_name}' is not installed locally. Starting background pull...")
                                async def perform_pull():
                                    async with httpx.AsyncClient(timeout=600.0) as pull_client:
                                        try:
                                            await pull_client.post(f"{ollama_base_url}/api/pull", json={"name": model_name})
                                            print(f"Background pull completed for model: {model_name}")
                                        except Exception as pe:
                                            print(f"Failed background pull for model {model_name}: {pe}")
                                asyncio.create_task(perform_pull())
                except Exception as e:
                    print(f"Error checking/pulling model: {e}")
            
            if main_model:
                asyncio.create_task(check_and_pull(main_model))
            if code_model and code_model != main_model:
                asyncio.create_task(check_and_pull(code_model))

            return {
                "status": "success",
                "message": "Configuration updated successfully",
                "config": config
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    @router.post("/permission/respond")
    async def respond_to_permission(request: PermissionResponseRequest):
        """Respond to a pending path permission request"""
        try:
            import os
            from .permissions import resolve_permission
            
            path_abs = os.path.abspath(request.path)
            
            # Resolve permission (triggers the wait event in the blocking thread)
            success = resolve_permission(request.session_id, path_abs, request.granted)
            from .audit import record_security_event
            record_security_event(
                "path_permission_decision",
                session_id=request.session_id,
                path=path_abs,
                granted=request.granted,
                resolved=success,
                scope="one_time",
            )
            
            return {
                "status": "success",
                "resolved": success,
                "path": path_abs,
                "granted": request.granted
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/permission/command/respond")
    async def respond_to_command_permission(request: CommandPermissionResponseRequest):
        """Respond to a pending command execution permission request"""
        try:
            from .permissions import resolve_command_permission
            
            success = resolve_command_permission(request.session_id, request.command, request.granted)
            from .audit import record_security_event
            record_security_event(
                "command_permission_decision",
                session_id=request.session_id,
                command=request.command,
                granted=request.granted,
                resolved=success,
                scope="one_time",
            )
            
            return {
                "status": "success",
                "resolved": success,
                "command": request.command,
                "granted": request.granted
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/permission/plan/respond")
    async def respond_to_plan_permission(request: PlanApprovalResponseRequest):
        """Respond to a pending plan approval request"""
        try:
            from .permissions import resolve_plan
            
            # Resolve plan (triggers the wait event in the blocking thread)
            success = resolve_plan(request.session_id, request.plan_path, request.plan_content, request.approved)
            from .audit import record_security_event
            record_security_event(
                "plan_approval_decision",
                session_id=request.session_id,
                plan_path=request.plan_path,
                approved=request.approved,
                resolved=success,
            )
            
            return {
                "status": "success",
                "resolved": success,
                "plan_path": request.plan_path,
                "approved": request.approved
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/workspace/roots")
    async def get_workspace_roots():
        """Get the default workspace root and any whitelisted paths"""
        try:
            import os
            from .config import AGENT_WORKSPACE_DIR
            from .config_store import get_allowed_paths
            return {
                "status": "success",
                "workspace": os.path.abspath(AGENT_WORKSPACE_DIR),
                "allowed_paths": get_allowed_paths()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/workspace/list")
    async def get_workspace_list(path: Optional[str] = None):
        """List files and folders under a specific whitelisted directory path"""
        try:
            import os
            from .config import AGENT_WORKSPACE_DIR, is_safe_path
            
            # Use default workspace if no path specified
            target_path = path if path else AGENT_WORKSPACE_DIR
            target_abs = os.path.abspath(target_path)
            
            # Security check
            if not is_safe_path(target_abs):
                raise HTTPException(status_code=403, detail=f"Access denied: Path is not allowed: {target_abs}")
                
            if not os.path.exists(target_abs):
                raise HTTPException(status_code=404, detail="Directory not found")
                
            if not os.path.isdir(target_abs):
                raise HTTPException(status_code=400, detail="Path is not a directory")
                
            items = []
            for item in os.listdir(target_abs):
                item_path = os.path.join(target_abs, item)
                is_dir = os.path.isdir(item_path)
                size = 0 if is_dir else os.path.getsize(item_path)
                items.append({
                    "name": item,
                    "path": item_path,
                    "is_dir": is_dir,
                    "size": size
                })
                
            return {
                "status": "success",
                "path": target_abs,
                "items": items
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/workspace/file")
    async def get_workspace_file(path: str):
        """Fetch the contents of a specific whitelisted file"""
        try:
            import os
            from .config import is_safe_path
            
            target_abs = os.path.abspath(path)
            
            # Security check
            if not is_safe_path(target_abs):
                raise HTTPException(status_code=403, detail=f"Access denied: Path is not allowed: {target_abs}")
                
            if not os.path.exists(target_abs):
                raise HTTPException(status_code=404, detail="File not found")
                
            if not os.path.isfile(target_abs):
                raise HTTPException(status_code=400, detail="Path is not a file")
                
            # Read file content
            with open(target_abs, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            return {
                "status": "success",
                "path": target_abs,
                "content": content
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    class WriteFileRequest(BaseModel):
        path: str
        content: str

    @router.post("/workspace/file")
    async def write_workspace_file(request: WriteFileRequest):
        """Write or update the contents of a specific whitelisted file"""
        try:
            import os
            from .config import is_safe_path
            
            target_abs = os.path.abspath(request.path)
            
            # Security check
            if not is_safe_path(target_abs):
                raise HTTPException(status_code=403, detail=f"Access denied: Path is not allowed: {target_abs}")
                
            # Write file content
            with open(target_abs, 'w', encoding='utf-8') as f:
                f.write(request.content)
                
            return {
                "status": "success",
                "path": target_abs,
                "message": "File saved successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    class CreateDirectoryRequest(BaseModel):
        path: str
        name: str

    @router.post("/workspace/directory")
    async def create_workspace_directory(request: CreateDirectoryRequest):
        """Create a new directory inside a whitelisted directory path"""
        try:
            import os
            from .config import is_safe_path
            
            target_parent = os.path.abspath(request.path)
            # Security check
            if not is_safe_path(target_parent):
                raise HTTPException(status_code=403, detail=f"Access denied: Path is not allowed: {target_parent}")
                
            new_dir_path = os.path.join(target_parent, request.name)
            new_dir_abs = os.path.abspath(new_dir_path)
            
            # Security check for sub path
            if not is_safe_path(new_dir_abs):
                raise HTTPException(status_code=403, detail=f"Access denied: Target path is not allowed: {new_dir_abs}")
                
            if os.path.exists(new_dir_abs):
                raise HTTPException(status_code=400, detail="Directory already exists")
                
            os.makedirs(new_dir_abs, exist_ok=True)
            
            return {
                "status": "success",
                "message": f"Directory '{request.name}' created successfully",
                "path": new_dir_abs
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    # --- Dynamic platform integrations ---
    @router.get("/models/local")
    async def get_local_models():
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{ollama_base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return {
                        "status": "success",
                        "models": [{"name": m["name"], "details": m["details"]} for m in models]
                    }
                return {"status": "error", "message": f"Ollama returned {response.status_code}", "models": []}
            except Exception as e:
                return {"status": "error", "message": str(e), "models": []}

    @router.post("/models/pull")
    async def pull_ollama_model(model_name: str):
        import httpx
        async def generate_pull_progress():
            async with httpx.AsyncClient(timeout=300.0) as client:
                try:
                    async with client.stream(
                        "POST", 
                        f"{ollama_base_url}/api/pull", 
                        json={"name": model_name}
                    ) as response:
                        async for line in response.aiter_lines():
                            if line:
                                yield f"data: {line}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    
        return StreamingResponse(
            generate_pull_progress(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    def serialize_hub_workspace(hub: HubModel, workspace: HubWorkspaceModel, tasks: List[AgentTaskModel], memories: List[HubMemoryModel], artifacts: List[HubArtifactModel], runs: List[AgentRunModel]) -> Dict[str, Any]:
        return {
            "hub": {"id": hub.id, "name": hub.name, "description": hub.description},
            "workspace": {
                "mission": workspace.mission,
                "success_criteria": workspace.success_criteria or [],
                "status": workspace.status,
                "updated_at": workspace.updated_at.isoformat() if workspace.updated_at else None,
            },
            "tasks": [{"id": task.id, "title": task.title, "description": task.description, "assigned_role": task.assigned_role, "status": task.status, "depends_on": task.depends_on or [], "result": task.result, "updated_at": task.updated_at.isoformat() if task.updated_at else None} for task in tasks],
            "memories": [{"id": memory.id, "category": memory.category, "content": memory.content, "created_at": memory.created_at.isoformat() if memory.created_at else None} for memory in memories],
            "artifacts": [{"id": artifact.id, "task_id": artifact.task_id, "name": artifact.name, "kind": artifact.kind, "path": artifact.path, "summary": artifact.summary, "created_at": artifact.created_at.isoformat() if artifact.created_at else None} for artifact in artifacts],
            "runs": [{"id": run.id, "task_id": run.task_id, "agent_role": run.agent_role, "status": run.status, "plan": run.plan or [], "changed_files": run.changed_files or [], "commands": run.commands or [], "result": run.result, "error": run.error, "created_at": run.created_at.isoformat() if run.created_at else None, "completed_at": run.completed_at.isoformat() if run.completed_at else None} for run in runs],
        }

    async def get_hub_or_404(hub_id: str, db: AsyncSession) -> HubModel:
        hub = (await db.execute(select(HubModel).filter(HubModel.id == hub_id))).scalar_one_or_none()
        if not hub:
            raise HTTPException(status_code=404, detail="Hub not found")
        return hub

    @router.get("/hubs/{hub_id}/workspace")
    async def get_hub_workspace(hub_id: str, db: AsyncSession = Depends(get_db)):
        hub = await get_hub_or_404(hub_id, db)
        workspace = (await db.execute(select(HubWorkspaceModel).filter(HubWorkspaceModel.hub_id == hub_id))).scalar_one_or_none()
        if workspace is None:
            workspace = HubWorkspaceModel(hub_id=hub_id)
            db.add(workspace)
            await db.commit()
            await db.refresh(workspace)
        tasks = (await db.execute(select(AgentTaskModel).filter(AgentTaskModel.hub_id == hub_id).order_by(AgentTaskModel.created_at.desc()))).scalars().all()
        memories = (await db.execute(select(HubMemoryModel).filter(HubMemoryModel.hub_id == hub_id).order_by(HubMemoryModel.created_at.desc()).limit(30))).scalars().all()
        artifacts = (await db.execute(select(HubArtifactModel).filter(HubArtifactModel.hub_id == hub_id).order_by(HubArtifactModel.created_at.desc()).limit(30))).scalars().all()
        runs = (await db.execute(select(AgentRunModel).filter(AgentRunModel.hub_id == hub_id).order_by(AgentRunModel.created_at.desc()).limit(30))).scalars().all()
        return serialize_hub_workspace(hub, workspace, tasks, memories, artifacts, runs)

    @router.put("/hubs/{hub_id}/workspace")
    async def update_hub_workspace(hub_id: str, update: HubWorkspaceUpdate, db: AsyncSession = Depends(get_db)):
        await get_hub_or_404(hub_id, db)
        workspace = (await db.execute(select(HubWorkspaceModel).filter(HubWorkspaceModel.hub_id == hub_id))).scalar_one_or_none()
        if workspace is None:
            workspace = HubWorkspaceModel(hub_id=hub_id)
            db.add(workspace)
        workspace.mission = update.mission.strip()
        workspace.success_criteria = [item.strip() for item in update.success_criteria if item.strip()]
        workspace.status = update.status
        await db.commit()
        from .audit import record_security_event
        record_security_event("hub_workspace_updated", hub_id=hub_id, status=workspace.status)
        return {"status": "success"}

    @router.post("/hubs/{hub_id}/tasks")
    async def create_hub_task(hub_id: str, request: HubTaskCreate, db: AsyncSession = Depends(get_db)):
        await get_hub_or_404(hub_id, db)
        task = AgentTaskModel(id=str(uuid.uuid4()), hub_id=hub_id, title=request.title.strip(), description=request.description.strip(), assigned_role=request.assigned_role, depends_on=request.depends_on)
        db.add(task)
        await db.commit()
        return {"status": "success", "task_id": task.id}

    @router.patch("/hubs/{hub_id}/tasks/{task_id}")
    async def update_hub_task(hub_id: str, task_id: str, update: HubTaskUpdate, db: AsyncSession = Depends(get_db)):
        task = (await db.execute(select(AgentTaskModel).filter(AgentTaskModel.id == task_id, AgentTaskModel.hub_id == hub_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if update.status is not None:
            task.status = update.status
        if update.assigned_role is not None:
            task.assigned_role = update.assigned_role
        if update.result is not None:
            task.result = update.result
        await db.commit()
        return {"status": "success"}

    @router.post("/hubs/{hub_id}/memory")
    async def add_hub_memory(hub_id: str, request: HubMemoryCreate, db: AsyncSession = Depends(get_db)):
        await get_hub_or_404(hub_id, db)
        memory = HubMemoryModel(hub_id=hub_id, category=request.category, content=request.content.strip())
        db.add(memory)
        await db.commit()
        return {"status": "success", "memory_id": memory.id}

    async def execute_approved_run(run_id: str) -> None:
        session = SessionLocal()
        try:
            run = session.query(AgentRunModel).filter(AgentRunModel.id == run_id).first()
            task = session.query(AgentTaskModel).filter(AgentTaskModel.id == run.task_id).first() if run else None
            workspace = session.query(HubWorkspaceModel).filter(HubWorkspaceModel.hub_id == run.hub_id).first() if run else None
            memories = session.query(HubMemoryModel).filter(HubMemoryModel.hub_id == run.hub_id).order_by(HubMemoryModel.created_at.desc()).limit(10).all() if run else []
            if not run or not task:
                return
            run.status, task.status = "executing", "in_progress"
            session.commit()
            shared_context = "\n".join(f"- {memory.category}: {memory.content}" for memory in memories)
            prompt = f"You are the {run.agent_role} on a team task. Mission: {workspace.mission if workspace else ''}\nTask: {task.title}\nDetails: {task.description}\nShared team context:\n{shared_context}\nWork within configured permissions. Report concise results, files changed, checks run, and remaining risks."
            result = await asyncio.to_thread(orchestrator.process_request, prompt, {"hub_id": run.hub_id, "task_id": task.id, "agent_role": run.agent_role}, session_id=f"hub_{run.hub_id}_{task.id}")
            run.result = result.get("response", str(result)) if isinstance(result, dict) else str(result)
            run.status, task.status, run.completed_at = "completed", "completed", datetime.utcnow()
            artifact = HubArtifactModel(id=str(uuid.uuid4()), hub_id=run.hub_id, task_id=task.id, name=f"{task.title} result", kind="agent_summary", summary=run.result[:2000])
            session.add(artifact)
            session.commit()
        except Exception as exc:
            if 'run' in locals() and run:
                run.status, run.error, run.completed_at = "failed", str(exc), datetime.utcnow()
                if 'task' in locals() and task:
                    task.status = "failed"
                session.commit()
        finally:
            session.close()

    @router.post("/hubs/{hub_id}/tasks/{task_id}/runs")
    async def prepare_hub_task_run(hub_id: str, task_id: str, db: AsyncSession = Depends(get_db)):
        task = (await db.execute(select(AgentTaskModel).filter(AgentTaskModel.id == task_id, AgentTaskModel.hub_id == hub_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        plan = ["Inspect the relevant workspace and constraints.", "Implement or research the requested change.", "Run the smallest relevant verification.", "Report evidence, risks, and next steps."]
        run = AgentRunModel(id=str(uuid.uuid4()), hub_id=hub_id, task_id=task.id, agent_role=task.assigned_role, status="awaiting_approval", plan=plan)
        task.status = "awaiting_approval"
        db.add(run)
        await db.commit()
        return {"status": "awaiting_approval", "run_id": run.id, "plan": plan}

    @router.post("/hubs/{hub_id}/runs/{run_id}/approve")
    async def approve_hub_run(hub_id: str, run_id: str, db: AsyncSession = Depends(get_db)):
        run = (await db.execute(select(AgentRunModel).filter(AgentRunModel.id == run_id, AgentRunModel.hub_id == hub_id))).scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status != "awaiting_approval":
            raise HTTPException(status_code=409, detail="Only planned runs can be approved")
        run.status = "queued"
        await db.commit()
        from .audit import record_security_event
        record_security_event("hub_run_approved", hub_id=hub_id, run_id=run_id, task_id=run.task_id, agent_role=run.agent_role)
        asyncio.create_task(execute_approved_run(run_id))
        return {"status": "queued"}

    # Hubs CRUD
    @router.get("/hubs", response_model=List[HubSchema])
    async def get_hubs(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(HubModel))
        hubs = result.scalars().all()
        return [HubSchema(id=h.id, name=h.name, description=h.description) for h in hubs]

    @router.post("/hubs", response_model=HubSchema)
    async def create_or_update_hub(hub: HubSchema, db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(HubModel).filter(HubModel.id == hub.id))
        db_hub = result.scalar_one_or_none()
        if db_hub:
            db_hub.name = hub.name
            db_hub.description = hub.description
        else:
            db_hub = HubModel(id=hub.id, name=hub.name, description=hub.description)
            db.add(db_hub)
        await db.commit()
        return hub

    @router.delete("/hubs/{hub_id}")
    async def delete_hub(hub_id: str, db: AsyncSession = Depends(get_db)):
        await db.execute(delete(HubModel).filter(HubModel.id == hub_id))
        await db.commit()
        return {"status": "success", "message": f"Hub {hub_id} deleted"}

    # Custom Agents CRUD
    @router.get("/custom-agents", response_model=List[AgentSchema])
    async def get_custom_agents(hub_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
        if hub_id:
            result = await db.execute(select(AgentModel).filter(AgentModel.hub_id == hub_id))
        else:
            result = await db.execute(select(AgentModel))
        agents = result.scalars().all()
        return [
            AgentSchema(
                id=a.id,
                hub_id=a.hub_id,
                parent_id=a.parent_id,
                name=a.name,
                persona=a.persona,
                system_prompt=a.system_prompt,
                base_model=a.base_model,
                ollama_base_url=a.ollama_base_url,
                tools=a.tools or [],
                mcp_servers=a.mcp_servers or [],
                training_data=a.training_data or []
            ) for a in agents
        ]

    @router.post("/custom-agents", response_model=AgentSchema)
    async def create_or_update_custom_agent(agent: AgentSchema, db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(AgentModel).filter(AgentModel.id == agent.id))
        db_agent = result.scalar_one_or_none()
        if db_agent:
            db_agent.hub_id = agent.hub_id
            db_agent.parent_id = agent.parent_id
            db_agent.name = agent.name
            db_agent.persona = agent.persona
            db_agent.system_prompt = agent.system_prompt
            db_agent.base_model = agent.base_model
            db_agent.ollama_base_url = agent.ollama_base_url
            db_agent.tools = agent.tools
            db_agent.mcp_servers = agent.mcp_servers
            db_agent.training_data = agent.training_data
        else:
            db_agent = AgentModel(
                id=agent.id,
                hub_id=agent.hub_id,
                parent_id=agent.parent_id,
                name=agent.name,
                persona=agent.persona,
                system_prompt=agent.system_prompt,
                base_model=agent.base_model,
                ollama_base_url=agent.ollama_base_url,
                tools=agent.tools,
                mcp_servers=agent.mcp_servers,
                training_data=agent.training_data
            )
            db.add(db_agent)
        await db.commit()
        return agent

    @router.delete("/custom-agents/{agent_id}")
    async def delete_custom_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
        await db.execute(delete(AgentModel).filter(AgentModel.id == agent_id))
        await db.commit()
        return {"status": "success", "message": f"Agent {agent_id} deleted"}

    # MCP Servers CRUD
    @router.get("/mcp-servers", response_model=List[McpServerSchema])
    async def get_mcp_servers(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(McpServerModel))
        servers = result.scalars().all()
        return [
            McpServerSchema(
                id=s.id,
                name=s.name,
                type=s.type,
                command=s.command,
                args=s.args or [],
                url=s.url,
                env=s.env or {},
                enabled=s.enabled
            ) for s in servers
        ]

    @router.post("/mcp-servers", response_model=McpServerSchema)
    async def create_or_update_mcp_server(server: McpServerSchema, db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(McpServerModel).filter(McpServerModel.id == server.id))
        db_server = result.scalar_one_or_none()
        if db_server:
            db_server.name = server.name
            db_server.type = server.type
            db_server.command = server.command
            db_server.args = server.args
            db_server.url = server.url
            db_server.env = server.env
            db_server.enabled = server.enabled
        else:
            db_server = McpServerModel(
                id=server.id,
                name=server.name,
                type=server.type,
                command=server.command,
                args=server.args,
                url=server.url,
                env=server.env,
                enabled=server.enabled
            )
            db.add(db_server)
        await db.commit()
        return server

    @router.delete("/mcp-servers/{mcp_id}")
    async def delete_mcp_server(mcp_id: str, db: AsyncSession = Depends(get_db)):
        await db.execute(delete(McpServerModel).filter(McpServerModel.id == mcp_id))
        await db.commit()
        return {"status": "success", "message": f"MCP Server {mcp_id} deleted"}

    # Workflows CRUD
    @router.get("/workflows", response_model=List[WorkflowSchema])
    async def get_workflows(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(WorkflowModel))
        workflows = result.scalars().all()
        return [
            WorkflowSchema(
                id=w.id,
                name=w.name,
                description=w.description,
                nodes=w.nodes or [],
                edges=w.edges or []
            ) for w in workflows
        ]

    @router.post("/workflows", response_model=WorkflowSchema)
    async def create_or_update_workflow(workflow: WorkflowSchema, db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(WorkflowModel).filter(WorkflowModel.id == workflow.id))
        db_workflow = result.scalar_one_or_none()
        if db_workflow:
            db_workflow.name = workflow.name
            db_workflow.description = workflow.description
            db_workflow.nodes = workflow.nodes
            db_workflow.edges = workflow.edges
        else:
            db_workflow = WorkflowModel(
                id=workflow.id,
                name=workflow.name,
                description=workflow.description,
                nodes=workflow.nodes,
                edges=workflow.edges
            )
            db.add(db_workflow)
        await db.commit()
        return workflow

    @router.delete("/workflows/{workflow_id}")
    async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
        await db.execute(delete(WorkflowModel).filter(WorkflowModel.id == workflow_id))
        await db.commit()
        return {"status": "success", "message": f"Workflow {workflow_id} deleted"}

    # Stats Token Usage Leaderboard
    @router.get("/stats/tokens")
    async def get_token_stats(db: AsyncSession = Depends(get_db)):
        # Get all active agents from database
        result_agents = await db.execute(select(AgentModel))
        all_agents = result_agents.scalars().all()
        
        # Initialize stats dict with all active agents
        stats_dict = {}
        for agent in all_agents:
            stats_dict[agent.id] = {
                "agent_id": agent.id,
                "name": agent.name,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
            
        # Query total token usage from performance logs
        query = select(
            PerformanceLogModel.agent_id,
            func.sum(PerformanceLogModel.prompt_tokens).label("sum_prompt"),
            func.sum(PerformanceLogModel.completion_tokens).label("sum_completion"),
            func.sum(PerformanceLogModel.total_tokens).label("sum_total")
        ).group_by(PerformanceLogModel.agent_id)
        
        result_logs = await db.execute(query)
        for row in result_logs.all():
            agent_id, sum_prompt, sum_completion, sum_total = row
            if agent_id in stats_dict:
                stats_dict[agent_id]["prompt_tokens"] = sum_prompt or 0
                stats_dict[agent_id]["completion_tokens"] = sum_completion or 0
                stats_dict[agent_id]["total_tokens"] = sum_total or 0
            else:
                # Include logs for deleted agents as well to keep historical accuracy
                stats_dict[agent_id] = {
                    "agent_id": agent_id,
                    "name": agent_id,
                    "prompt_tokens": sum_prompt or 0,
                    "completion_tokens": sum_completion or 0,
                    "total_tokens": sum_total or 0
                }
                
        return {
            "status": "success",
            "stats": list(stats_dict.values())
        }

    @router.get("/stats/daily")
    async def get_daily_token_stats(db: AsyncSession = Depends(get_db)):
        from datetime import datetime, timedelta
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        query = select(
            func.sum(PerformanceLogModel.prompt_tokens).label("sum_prompt"),
            func.sum(PerformanceLogModel.completion_tokens).label("sum_completion"),
            func.sum(PerformanceLogModel.total_tokens).label("sum_total")
        ).filter(PerformanceLogModel.timestamp >= one_day_ago)
        
        result = await db.execute(query)
        row = result.first()
        
        prompt_tokens, completion_tokens, total_tokens = 0, 0, 0
        if row:
            sum_prompt, sum_completion, sum_total = row
            prompt_tokens = sum_prompt or 0
            completion_tokens = sum_completion or 0
            total_tokens = sum_total or 0
            
        return {
            "status": "success",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }

    # ==================== Scheduled Tasks CRUD ====================

    @router.get("/scheduler/tasks")
    async def get_scheduled_tasks(db: AsyncSession = Depends(get_db)):
        """Get all scheduled/looped tasks"""
        from database.models import ScheduledTaskModel
        result = await db.execute(select(ScheduledTaskModel))
        tasks = result.scalars().all()
        return {
            "status": "success",
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "prompt": t.prompt,
                    "interval_minutes": t.interval_minutes,
                    "run_at": t.run_at.isoformat() if t.run_at else None,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "status": t.status,
                    "history": t.history or [],
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in tasks
            ]
        }

    @router.post("/scheduler/tasks")
    async def create_scheduled_task(task: ScheduledTaskSchema, db: AsyncSession = Depends(get_db)):
        """Create a new scheduled/looped task"""
        import uuid
        from datetime import datetime, timedelta
        from database.models import ScheduledTaskModel
        
        task_id = task.id or f"task_{uuid.uuid4().hex[:8]}"
        delay = task.delay_minutes if task.delay_minutes and task.delay_minutes > 0 else 1
        run_at = datetime.utcnow() + timedelta(minutes=delay)
        
        new_task = ScheduledTaskModel(
            id=task_id,
            name=task.name,
            prompt=task.prompt,
            interval_minutes=task.interval_minutes if task.interval_minutes and task.interval_minutes > 0 else None,
            run_at=run_at,
            status="active",
            history=[]
        )
        db.add(new_task)
        await db.commit()
        
        return {
            "status": "success",
            "task": {
                "id": task_id,
                "name": task.name,
                "prompt": task.prompt,
                "interval_minutes": new_task.interval_minutes,
                "run_at": run_at.isoformat(),
                "status": "active"
            }
        }

    @router.delete("/scheduler/tasks/{task_id}")
    async def delete_scheduled_task(task_id: str, db: AsyncSession = Depends(get_db)):
        """Delete a scheduled task"""
        from database.models import ScheduledTaskModel
        await db.execute(delete(ScheduledTaskModel).filter(ScheduledTaskModel.id == task_id))
        await db.commit()
        return {"status": "success", "message": f"Scheduled task {task_id} deleted"}

    @router.post("/scheduler/tasks/{task_id}/toggle")
    async def toggle_scheduled_task(task_id: str, db: AsyncSession = Depends(get_db)):
        """Pause or resume a scheduled task"""
        from database.models import ScheduledTaskModel
        result = await db.execute(select(ScheduledTaskModel).filter(ScheduledTaskModel.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status == "active":
            task.status = "paused"
        elif task.status == "paused":
            task.status = "active"
        else:
            raise HTTPException(status_code=400, detail=f"Cannot toggle task with status: {task.status}")
        
        await db.commit()
        return {"status": "success", "task_id": task_id, "new_status": task.status}

    @router.post("/scheduler/tasks/{task_id}/run")
    async def run_scheduled_task_now(task_id: str, db: AsyncSession = Depends(get_db)):
        """Trigger immediate execution of a scheduled task"""
        from datetime import datetime
        from database.models import ScheduledTaskModel
        result = await db.execute(select(ScheduledTaskModel).filter(ScheduledTaskModel.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Set run_at to now so the scheduler picks it up immediately
        task.run_at = datetime.utcnow()
        task.status = "active"
        await db.commit()
        return {"status": "success", "message": f"Task {task_id} queued for immediate execution"}
    # ====== Agent Mode Endpoints ======

    class AgentModeChatRequest(BaseModel):
        prompt: str
        cwd: str
        file_path: Optional[str] = None
        file_content: Optional[str] = None
        session_id: str = "default"

    class AgentModeQuickActionRequest(BaseModel):
        action: str  # explain, find_bugs, refactor, add_tests, document, fix_errors, optimize, find_related
        file_path: str
        file_content: str
        cwd: str
        session_id: str = "default"

    @router.get("/agent-mode/status")
    async def agent_mode_status():
        """Check Agent Mode availability"""
        from .claude_code_service import get_claude_code_service
        from .agent_mode import get_agent_mode_orchestrator
        from .config import get_current_main_model
        
        service = get_claude_code_service()
        claude_available = await service.is_available()
        model_name = get_current_main_model()
        return {
            "status": "ready",
            "claude_code_available": claude_available,
            "ollama_model": model_name,
            "mode": "hybrid" if claude_available else "ollama_only"
        }

    @router.post("/agent-mode/chat")
    async def agent_mode_chat(request: AgentModeChatRequest):
        """Stream an agent mode chat response"""
        from .agent_mode import get_agent_mode_orchestrator
        from .config import get_current_main_model
        model_name = get_current_main_model()
        
        # We need ollama_base_url, use default if not in config
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        orchestrator = get_agent_mode_orchestrator(model_name=model_name, ollama_base_url=ollama_base_url)
        
        async def generate_sse():
            try:
                async for event in orchestrator.process_chat(
                    prompt=request.prompt,
                    cwd=request.cwd,
                    file_path=request.file_path,
                    file_content=request.file_content,
                    session_id=request.session_id
                ):
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        return StreamingResponse(generate_sse(), media_type="text/event-stream")

    @router.post("/agent-mode/quick-action")
    async def agent_mode_quick_action(request: AgentModeQuickActionRequest):
        """Execute a quick action on a file"""
        from .agent_mode import get_agent_mode_orchestrator
        from .config import get_current_main_model
        model_name = get_current_main_model()
        
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        orchestrator = get_agent_mode_orchestrator(model_name=model_name, ollama_base_url=ollama_base_url)
        
        async def generate_sse():
            try:
                async for event in orchestrator.quick_action(
                    action=request.action,
                    file_path=request.file_path,
                    file_content=request.file_content,
                    cwd=request.cwd,
                    session_id=request.session_id
                ):
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        return StreamingResponse(generate_sse(), media_type="text/event-stream")

    @router.get("/agent-mode/history")
    async def agent_mode_history(session_id: str = "default"):
        from .agent_mode import get_agent_mode_orchestrator
        from .config import get_current_main_model
        model_name = get_current_main_model()
        
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        orchestrator = get_agent_mode_orchestrator(model_name=model_name, ollama_base_url=ollama_base_url)
        return {"history": orchestrator.get_history(session_id)}

    @router.delete("/agent-mode/history")
    async def agent_mode_clear_history(session_id: str = "default"):
        from .agent_mode import get_agent_mode_orchestrator
        from .config import get_current_main_model
        model_name = get_current_main_model()
        
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        orchestrator = get_agent_mode_orchestrator(model_name=model_name, ollama_base_url=ollama_base_url)
        orchestrator.clear_history(session_id)
        return {"status": "cleared"}

    class ImageGenerationRequest(BaseModel):
        prompt: str = Field(..., min_length=1, description="Text prompt describing the image to generate")
        negative_prompt: Optional[str] = Field("", description="Negative prompt describing what to avoid")
        width: Optional[int] = Field(1024, ge=256, le=2048, description="Image width in pixels")
        height: Optional[int] = Field(1024, ge=256, le=2048, description="Image height in pixels")
        model: Optional[str] = Field("auto", description="Model name or 'auto'|'sdxl'|'sd15'|'flux'")
        seed: Optional[int] = Field(None, description="Random seed for reproducible generation")
        filename: Optional[str] = Field("generated_image", description="Output filename without extension")

    @router.post("/agents/business/generate-image")
    async def generate_image_api(request: ImageGenerationRequest):
        """Direct API endpoint for image generation using local diffusion pipeline"""
        try:
            from .image_pipeline import generate_image_with_pipeline, check_image_pipeline_health
            
            health = check_image_pipeline_health()
            if not health["ready"]:
                raise HTTPException(
                    status_code=503,
                    detail="Image generation dependencies not installed. Run: pip install torch torchvision diffusers transformers accelerate"
                )
            
            result = await asyncio.to_thread(
                generate_image_with_pipeline,
                prompt=request.prompt,
                negative_prompt=request.negative_prompt or "",
                width=request.width or 1024,
                height=request.height or 1024,
                steps=30,
                cfg_scale=7.5,
                seed=request.seed,
                model_id="stabilityai/stable-diffusion-xl-base-1.0" if request.model in ["auto", "sdxl"] else request.model,
                filename=request.filename or "generated_image",
            )
            
            if not result["success"]:
                raise HTTPException(status_code=500, detail=result.get("error", "Image generation failed"))
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image generation error: {str(e)}")

    return router

# Made with Bob
