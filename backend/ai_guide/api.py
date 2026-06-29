"""
AI Guide Backend - API Router
FastAPI router for the AI Guide chat endpoint
"""

import json
import logging
from typing import AsyncGenerator
import httpx

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import litellm

from .config import AIGuideConfig
from .models import (
    ChatMessage,
    GuideChatRequest,
    GuideChatChunk,
    HealthResponse,
)

logger = logging.getLogger("ai_guide")


def create_guide_router(config: AIGuideConfig) -> APIRouter:
    """
    Create a FastAPI router for the AI Guide
    
    Args:
        config: AI Guide configuration
        
    Returns:
        Configured FastAPI router
    """
    router = APIRouter(tags=["AI Guide"])
    
    # Configure logging
    logging.basicConfig(level=config.log_level)
    
    async def check_ollama_status() -> tuple[bool, str]:
        """
        Check if Ollama is running and the model is available
        
        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check if Ollama is running
                response = await client.get(f"{config.api_base}/api/tags")
                if response.status_code != 200:
                    return False, f"Ollama is not responding properly (status: {response.status_code})"
                
                # Check if the model is available
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                if config.model_name not in model_names:
                    return False, f"Model '{config.model_name}' not found. Please run: ollama pull {config.model_name}"
                
                return True, ""
                
        except httpx.ConnectError:
            return False, f"Cannot connect to Ollama at {config.api_base}. Please start Ollama first."
        except httpx.TimeoutException:
            return False, f"Ollama connection timeout. Please check if Ollama is running at {config.api_base}"
        except Exception as e:
            return False, f"Error checking Ollama status: {str(e)}"
    
    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint"""
        is_available, error_msg = await check_ollama_status()
        
        return HealthResponse(
            status="healthy" if is_available else "unhealthy",
            version="1.0.0",
            model_provider=config.model_provider,
            model_name=config.model_name,
            message=error_msg if not is_available else None,
        )
    
    @router.post("/chat")
    async def chat(request: GuideChatRequest):
        """
        Chat endpoint with streaming response
        
        Args:
            request: Chat request with messages and context
            
        Returns:
            Streaming response with Server-Sent Events
        """
        try:
            # Check if Ollama is available before processing
            is_available, error_msg = await check_ollama_status()
            if not is_available:
                # Return error immediately
                async def error_response() -> AsyncGenerator[str, None]:
                    error_chunk = GuideChatChunk(error=error_msg)
                    yield f"data: {error_chunk.model_dump_json()}\n\n"
                
                return StreamingResponse(
                    error_response(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    }
                )
            
            def get_application_state_summary() -> str:
                """Query database and config to summarize current application state for the AI Guide"""
                try:
                    from database.db import SessionLocal
                    from database.models import AgentModel, ScheduledTaskModel, HubModel, McpServerModel
                    from agents.config_store import get_allowed_paths, get_allowed_commands
                    import os
                    from datetime import datetime
                    
                    session = SessionLocal()
                    try:
                        # 1. Custom Hubs
                        hubs = session.query(HubModel).all()
                        hubs_list = [f"- Hub: {h.name} (ID: {h.id})" for h in hubs]
                        hubs_summary = "\n".join(hubs_list) if hubs_list else "No team hubs created yet."

                        # 2. Custom Agents
                        agents = session.query(AgentModel).all()
                        agent_list = [f"- Agent: {a.name} ({a.base_model}) | Persona: {a.persona[:80]}..." for a in agents]
                        agents_summary = "\n".join(agent_list) if agent_list else "No custom agents created yet."
                        
                        # 3. Active loops & scheduled tasks
                        tasks = session.query(ScheduledTaskModel).all()
                        task_list = [
                            f"- Loop Task: {t.name} ({t.status}) | Prompt: '{t.prompt[:80]}...' (Repeat every {t.interval_minutes}m)" if t.interval_minutes 
                            else f"- Loop Task: {t.name} ({t.status}) | Prompt: '{t.prompt[:80]}...' (One-time)" 
                            for t in tasks
                        ]
                        tasks_summary = "\n".join(task_list) if task_list else "No scheduled loops or tasks active."

                        # 4. MCP Servers
                        servers = session.query(McpServerModel).all()
                        server_list = [f"- MCP Server: {s.name} ({s.type}) | Enabled: {s.enabled}" for s in servers]
                        servers_summary = "\n".join(server_list) if server_list else "No MCP servers registered."
                    finally:
                        session.close()
                    
                    # 5. Security Config
                    paths = get_allowed_paths()
                    commands = get_allowed_commands()
                    
                    paths_summary = "\n".join(f"- {p}" for p in paths) if paths else "No whitelisted folder paths configured."
                    commands_summary = "\n".join(f"- {c}" for c in commands) if commands else "No whitelisted commands configured."
                    
                    # 6. Workspace Files
                    from agents.config import AGENT_WORKSPACE_DIR
                    workspace_files_summary = ""
                    recent_files_summary = ""
                    if os.path.exists(AGENT_WORKSPACE_DIR) and os.path.isdir(AGENT_WORKSPACE_DIR):
                        try:
                            files = os.listdir(AGENT_WORKSPACE_DIR)
                            files_list = []
                            files_with_mtime = []
                            for f in files:
                                f_path = os.path.join(AGENT_WORKSPACE_DIR, f)
                                if os.path.isfile(f_path):
                                    files_list.append(f)
                                    files_with_mtime.append((f, os.path.getmtime(f_path)))
                                elif os.path.isdir(f_path) and not f.startswith('.'):
                                    files_list.append(f + "/")
                            
                            if files_list:
                                workspace_files_summary = "\n".join(f"- {name}" for name in files_list[:15])
                                if len(files_list) > 15:
                                    workspace_files_summary += f"\n- ... and {len(files_list) - 15} more files/folders"
                            else:
                                workspace_files_summary = "Workspace folder is empty."
                                
                            # Get 3 most recently modified files
                            files_with_mtime.sort(key=lambda x: x[1], reverse=True)
                            recent_files_summary = "\n".join(
                                f"- {name} (Modified: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')})" 
                                for name, mtime in files_with_mtime[:3]
                            )
                        except Exception as e:
                            workspace_files_summary = f"(Error reading workspace: {str(e)})"
                    else:
                        workspace_files_summary = "Workspace directory does not exist or is not set up."
                        
                    return f"""
CURRENT APPLICATION STATE:
=== CUSTOM HUB TEAMS ===
{hubs_summary}

=== CUSTOM AGENTS CREATED ===
{agents_summary}

=== ACTIVE LOOPS & SCHEDULED TASKS ===
{tasks_summary}

=== MCP SERVERS REGISTERED ===
{servers_summary}

=== SECURITY WHITELIST CONFIGURATION ===
* Whitelisted folder paths:
{paths_summary}

* Whitelisted terminal commands:
{commands_summary}

=== WORKSPACE DIRECTORY FILES ({os.path.basename(AGENT_WORKSPACE_DIR)}) ===
{workspace_files_summary}

=== RECENTLY MODIFIED FILES ===
{recent_files_summary if recent_files_summary else "No files modified recently."}
"""
                except Exception as e:
                    return f"\n(Error gathering application state summary: {str(e)})"

            # Build messages for LLM
            messages = []
            
            # Add system prompt with context and application state
            system_prompt = config.get_system_prompt(request.page_context)
            app_state = get_application_state_summary()
            full_system_prompt = f"{system_prompt}\n\n{app_state}"
            
            messages.append({
                "role": "system",
                "content": full_system_prompt
            })
            
            # Add conversation history
            for msg in request.messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Stream response
            async def stream_response() -> AsyncGenerator[str, None]:
                try:
                    # Get LiteLLM parameters
                    llm_params = config.get_litellm_params()
                    llm_params["messages"] = messages
                    
                    # Call LiteLLM with streaming
                    response = await litellm.acompletion(**llm_params)
                    
                    # Stream chunks
                    async for chunk in response:
                        # Access delta content safely
                        try:
                            delta = chunk.choices[0].delta  # type: ignore
                            if hasattr(delta, 'content') and delta.content:
                                chunk_data = GuideChatChunk(content=delta.content)
                                yield f"data: {chunk_data.model_dump_json()}\n\n"
                        except (AttributeError, IndexError):
                            continue
                    
                    # Send completion signal
                    done_chunk = GuideChatChunk(done=True)
                    yield f"data: {done_chunk.model_dump_json()}\n\n"
                    
                except Exception as e:
                    logger.error(f"Streaming error: {e}", exc_info=True)
                    # Provide helpful error message
                    error_message = str(e)
                    if "Connection" in error_message or "connect" in error_message.lower():
                        error_message = f"Cannot connect to Ollama. Please ensure Ollama is running and the model '{config.model_name}' is available."
                    elif "model" in error_message.lower():
                        error_message = f"Model '{config.model_name}' not found. Please run: ollama pull {config.model_name}"
                    error_chunk = GuideChatChunk(error=error_message)
                    yield f"data: {error_chunk.model_dump_json()}\n\n"
            
            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                }
            )
            
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    return router


def create_guide_app(config: AIGuideConfig) -> FastAPI:
    """
    Create a standalone FastAPI application for AI Guide
    
    Args:
        config: AI Guide configuration
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="AI Guide API",
        description="Backend API for AI Guide assistant",
        version="1.0.0",
    )
    
    # Add CORS middleware if enabled
    if config.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Include the guide router
    guide_router = create_guide_router(config)
    app.include_router(guide_router, prefix="/api/guide")
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "AI Guide API",
            "version": "1.0.0",
            "docs": "/docs",
        }
    
    return app

# Made with Bob
