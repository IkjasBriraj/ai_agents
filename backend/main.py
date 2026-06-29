import time
import json
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import MessageGraph

from database.db import get_db, init_db
from database.models import AgentModel, ChatMessageModel, PerformanceLogModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

# Import AI Guide
from ai_guide import create_guide_router, AIGuideConfig

# Import Multi-Agent System
from agents.api import create_multi_agent_router
from agents.config import DEFAULT_MAIN_MODEL

app = FastAPI(title="SeniorAgent Backend")

@app.on_event("startup")
async def startup_event():
    await init_db()
    # Start the background task scheduler
    from agents.scheduler import get_scheduler
    scheduler = get_scheduler(model_name=DEFAULT_MAIN_MODEL, ollama_base_url=OLLAMA_URL)
    await scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    from agents.scheduler import get_scheduler
    scheduler = get_scheduler()
    await scheduler.stop()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434"

class Agent(BaseModel):
    id: str
    name: str
    persona: str
    system_prompt: str
    tools: List[str] = []
    base_model: str = "qwen3.5:9b"
    training_data: List[Dict[str, str]] = []

class AgentPerformance(BaseModel):
    agent_id: str
    ttft: float  # Time to First Token
    total_time: float
    timestamp: float

class TrainingData(BaseModel):
    q: str
    a: str

class TrainingPayload(BaseModel):
    data: List[TrainingData]
    epochs: int = 3
    batch_size: int = 8
    learning_rate: float = 0.00002

# Helper functions for message conversion
def to_langchain_messages(db_messages) -> List[BaseMessage]:
    messages = []
    for msg in db_messages:
        if msg.role == "human":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "ai":
            messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            messages.append(SystemMessage(content=msg.content))
    return messages

class OllamaService:
    @staticmethod
    async def chat_stream(agent: Agent, prompt: str, history: Optional[List[BaseMessage]] = None, db: Optional[AsyncSession] = None):
        llm = ChatOllama(model=agent.base_model, base_url=OLLAMA_URL)
        
        messages = [SystemMessage(content=agent.system_prompt)]
        for data in agent.training_data:
            messages.append(HumanMessage(content=data.get("q", "")))
            messages.append(AIMessage(content=data.get("a", "")))
            
        if history:
            messages.extend(history)
            
        messages.append(HumanMessage(content=prompt))

        # Define a LangGraph workflow
        builder = MessageGraph()
        builder.add_node("oracle", llm)
        builder.set_entry_point("oracle")
        builder.set_finish_point("oracle")
        graph = builder.compile()
        
        start_time = time.time()
        ttft = None
        
        async for msg, metadata in graph.astream(messages, stream_mode="messages"):
            if msg.content:
                if ttft is None:
                    ttft = time.time() - start_time
                yield {"message": {"content": msg.content}, "done": False}
        
        total_time = time.time() - start_time
        if db:
            log = PerformanceLogModel(
                agent_id=agent.id,
                ttft=ttft or 0.0,
                total_time=total_time
            )
            db.add(log)
            await db.commit()
        yield {"done": True}

@app.get("/ollama/models")
async def get_ollama_models():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [{"name": m["name"], "details": m["details"]} for m in models]
            return []
        except Exception as e:
            print("Error fetching models:", e)
            return []

@app.get("/agents", response_model=List[Agent])
async def get_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentModel))
    db_agents = result.scalars().all()
    return [
        Agent(
            id=a.id,
            name=a.name,
            persona=a.persona,
            system_prompt=a.system_prompt,
            tools=a.tools or [],
            base_model=a.base_model,
            training_data=a.training_data or []
        ) for a in db_agents
    ]

@app.post("/agents")
async def create_agent(agent: Agent, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentModel).filter(AgentModel.id == agent.id))
    db_agent = result.scalar_one_or_none()
    
    if db_agent:
        db_agent.name = agent.name
        db_agent.persona = agent.persona
        db_agent.system_prompt = agent.system_prompt
        db_agent.tools = agent.tools
        db_agent.base_model = agent.base_model
        db_agent.training_data = agent.training_data
    else:
        db_agent = AgentModel(
            id=agent.id,
            name=agent.name,
            persona=agent.persona,
            system_prompt=agent.system_prompt,
            tools=agent.tools,
            base_model=agent.base_model,
            training_data=agent.training_data
        )
        db.add(db_agent)
        
    await db.commit()
    return agent

@app.post("/agents/{agent_id}/train")
async def train_agent(agent_id: str, payload: TrainingPayload, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentModel).filter(AgentModel.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    current_data = list(db_agent.training_data or [])
    for d in payload.data:
        current_data.append({"q": d.q, "a": d.a})
    db_agent.training_data = current_data
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(db_agent, "training_data")
    
    await db.commit()
    
    return {
        "status": "success", 
        "agent_id": db_agent.id, 
        "training_data_count": len(db_agent.training_data),
        "hyperparameters": {
            "epochs": payload.epochs,
            "batch_size": payload.batch_size,
            "learning_rate": payload.learning_rate
        }
    }

@app.get("/leaderboard")
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    query = select(
        PerformanceLogModel.agent_id,
        func.avg(PerformanceLogModel.ttft).label("avg_ttft"),
        func.avg(PerformanceLogModel.total_time).label("avg_total"),
        func.count(PerformanceLogModel.id).label("calls")
    ).group_by(PerformanceLogModel.agent_id)
    
    result = await db.execute(query)
    rows = result.all()
    
    leaderboard = []
    for row in rows:
        agent_id, avg_ttft, avg_total, calls = row
        agent_result = await db.execute(select(AgentModel).filter(AgentModel.id == agent_id))
        agent = agent_result.scalar_one_or_none()
        if agent:
            leaderboard.append({
                "id": agent_id,
                "name": agent.name,
                "avg_ttft": avg_ttft,
                "avg_total": avg_total,
                "calls": calls
            })
    
    return sorted(leaderboard, key=lambda x: x["avg_ttft"])

@app.post("/chat/{agent_id}")
async def chat(agent_id: str, prompt: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentModel).filter(AgentModel.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    agent = Agent(
        id=db_agent.id,
        name=db_agent.name,
        persona=db_agent.persona,
        system_prompt=db_agent.system_prompt,
        tools=db_agent.tools or [],
        base_model=db_agent.base_model if db_agent.base_model else DEFAULT_MAIN_MODEL,
        training_data=db_agent.training_data or []
    )
    
    session_id = f"chat_{agent_id}"
    history_result = await db.execute(
        select(ChatMessageModel)
        .filter(ChatMessageModel.session_id == session_id)
        .order_by(ChatMessageModel.timestamp.asc())
    )
    db_messages = history_result.scalars().all()
    history = to_langchain_messages(db_messages)
    
    # Save human message to database
    human_msg = ChatMessageModel(
        session_id=session_id,
        agent_id=agent_id,
        role="human",
        content=prompt
    )
    db.add(human_msg)
    await db.commit()
    
    full_response = ""
    async for chunk in OllamaService.chat_stream(agent, prompt, list(history), db=db):
        if "message" in chunk and chunk["message"].get("content"):
            full_response += chunk["message"]["content"]
            
    # Save AI message to database
    ai_msg = ChatMessageModel(
        session_id=session_id,
        agent_id=agent_id,
        role="ai",
        content=full_response
    )
    db.add(ai_msg)
    await db.commit()
    
    return {"response": full_response}

@app.post("/chat/{agent_id}/clear")
async def clear_chat(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentModel).filter(AgentModel.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    session_id = f"chat_{agent_id}"
    from sqlalchemy import delete
    await db.execute(delete(ChatMessageModel).filter(ChatMessageModel.session_id == session_id))
    await db.commit()
    return {"status": "success", "message": f"Conversation history for agent {agent_id} cleared"}

# Configure and mount AI Guide
guide_config = AIGuideConfig(
    model_provider="ollama",
    model_name=DEFAULT_MAIN_MODEL,
    api_base=OLLAMA_URL,
    system_prompt_template="""You are an AI assistant for the {context} section of the SeniorAgent application.

SeniorAgent helps users create, train, and manage AI agents with different personas and capabilities.

Available sections:
- Dashboard: Overview of all agents and their performance metrics
- Agent Builder: Create and configure new AI agents with custom personas
- Training: Fine-tune agents with custom training data
- Leaderboard: Compare agent performance (TTFT, response time)
- Chat: Test and interact with your agents

IMPORTANT RULES FOR YOUR RESPONSES:
1. Keep your answers EXTREMELY short and direct (1-3 sentences maximum).
2. If you are listing points, you MUST leave a completely blank line (double enter) after every single point. No large blocks of text!""",
    context_labels={
        "dashboard": "Dashboard",
        "builder": "Agent Builder",
        "training": "Training Center",
        "leaderboard": "Performance Leaderboard",
        "chat": "Agent Chat",
    },
    enable_cors=True,
    allowed_origins=["*"],
)

# Mount the AI Guide router
guide_router = create_guide_router(guide_config)
app.include_router(guide_router, prefix="/api/guide")

# Mount the Multi-Agent System router
multi_agent_router = create_multi_agent_router(
    model_name=DEFAULT_MAIN_MODEL,
    ollama_base_url=OLLAMA_URL
)
app.include_router(multi_agent_router, prefix="/api/multi-agent")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
