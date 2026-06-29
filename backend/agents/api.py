import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from database.db import get_db
from database.models import HubModel, AgentModel, McpServerModel, WorkflowModel, ChatMessageModel, PerformanceLogModel, ScheduledTaskModel
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from .orchestrator import OrchestratorAgent
from .specialized_agents import create_specialized_agent, SPECIALIZED_AGENTS
from .config import DEFAULT_MAIN_MODEL, DEFAULT_CODE_MODEL

class HubSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

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


class DirectAgentRequest(BaseModel):
    """Request model for direct agent interaction"""
    agent_type: str = Field(..., description="Agent type: code, research, or analysis")
    task: str = Field(..., description="Task for the agent")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")
    session_id: Optional[str] = Field(default="default", description="Session ID for agent memory")


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
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/agents/chat", response_model=AgentResponse)
    async def multi_agent_chat(request: MultiAgentRequest):
        """
        Chat with the multi-agent system
        The orchestrator will route to the appropriate specialized agent
        """
        try:
            session_id = request.session_id or "default"
            if request.stream:
                # Return streaming response
                async def generate():
                    async for chunk in orchestrator.process_request_stream(
                        request.prompt,
                        request.context,
                        session_id=session_id
                    ):
                        yield f"data: {json.dumps(chunk)}\n\n"
                
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
                result = await asyncio.to_thread(orchestrator.process_request, request.prompt, request.context, session_id=session_id)
                return AgentResponse(**result)
                
        except Exception as e:
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
    
    @router.get("/agents/health")
    async def health_check():
        """Health check for multi-agent system"""
        try:
            # Test orchestrator in a background thread to avoid blocking the event loop
            test_result = await asyncio.to_thread(orchestrator.process_request, "Hello")
            
            return {
                "status": "healthy",
                "orchestrator": "operational",
                "model": model_name,
                "available_agents": list(SPECIALIZED_AGENTS.keys()),
                "test_response": test_result.get("status") == "success"
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
            
            # If granted, add it to whitelisted config
            if request.granted:
                from .config_store import load_config, save_config
                config = load_config()
                allowed = config.get("allowed_paths", [])
                if path_abs not in allowed:
                    allowed.append(path_abs)
                    save_config(config)
            
            # Resolve permission (triggers the wait event in the blocking thread)
            success = resolve_permission(request.session_id, path_abs, request.granted)
            
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
            
            if request.granted:
                from .config_store import add_allowed_command
                add_allowed_command(request.command)
            
            success = resolve_command_permission(request.session_id, request.command, request.granted)
            
            return {
                "status": "success",
                "resolved": success,
                "command": request.command,
                "granted": request.granted
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
    
    return router

# Made with Bob
