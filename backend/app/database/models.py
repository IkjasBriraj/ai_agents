from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class HubModel(Base):
    """A Multi-Agent Hub is a team of agents working together on a set of tasks."""
    __tablename__ = "hubs"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agents = relationship("AgentModel", back_populates="hub", cascade="all, delete-orphan")
    workspace = relationship("HubWorkspaceModel", back_populates="hub", uselist=False, cascade="all, delete-orphan")
    tasks = relationship("AgentTaskModel", back_populates="hub", cascade="all, delete-orphan")
    memories = relationship("HubMemoryModel", back_populates="hub", cascade="all, delete-orphan")
    artifacts = relationship("HubArtifactModel", back_populates="hub", cascade="all, delete-orphan")
    runs = relationship("AgentRunModel", back_populates="hub", cascade="all, delete-orphan")


class HubWorkspaceModel(Base):
    """Goal and completion criteria for an agent team."""
    __tablename__ = "hub_workspaces"
    hub_id = Column(String, ForeignKey("hubs.id", ondelete="CASCADE"), primary_key=True)
    mission = Column(Text, default="")
    success_criteria = Column(JSON, default=list)
    status = Column(String, default="draft", index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    hub = relationship("HubModel", back_populates="workspace")


class AgentTaskModel(Base):
    """A delegated, reviewable unit of work inside a hub."""
    __tablename__ = "agent_tasks"
    id = Column(String, primary_key=True)
    hub_id = Column(String, ForeignKey("hubs.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    assigned_role = Column(String, default="lead")
    status = Column(String, default="queued", index=True)
    depends_on = Column(JSON, default=list)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    hub = relationship("HubModel", back_populates="tasks")


class HubMemoryModel(Base):
    """Explicit, user-visible context shared by a hub's agents."""
    __tablename__ = "hub_memories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hub_id = Column(String, ForeignKey("hubs.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String, default="decision")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    hub = relationship("HubModel", back_populates="memories")


class HubArtifactModel(Base):
    """A named output from a task, without storing its potentially large content."""
    __tablename__ = "hub_artifacts"
    id = Column(String, primary_key=True)
    hub_id = Column(String, ForeignKey("hubs.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    kind = Column(String, default="summary")
    path = Column(Text, nullable=True)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    hub = relationship("HubModel", back_populates="artifacts")


class AgentRunModel(Base):
    """Execution lifecycle and evidence for a delegated task."""
    __tablename__ = "agent_runs"
    id = Column(String, primary_key=True)
    hub_id = Column(String, ForeignKey("hubs.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_role = Column(String, default="lead")
    status = Column(String, default="planning", index=True)
    plan = Column(JSON, default=list)
    changed_files = Column(JSON, default=list)
    commands = Column(JSON, default=list)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    hub = relationship("HubModel", back_populates="runs")

class AgentModel(Base):
    """An individual agent with a custom prompt, model, tools, and parent delegation link."""
    __tablename__ = "agents"
    id = Column(String, primary_key=True)
    hub_id = Column(String, ForeignKey("hubs.id", ondelete="CASCADE"), nullable=True)
    parent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True) # Self-referential for sub-agents
    name = Column(String, nullable=False)
    persona = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    base_model = Column(String, default="granite4.1:8b")
    ollama_base_url = Column(String, default="http://localhost:11434")
    
    # Custom & system tool names, and registered MCP server IDs
    tools = Column(JSON, default=list) # e.g. ["file_operation", "github_search"]
    mcp_servers = Column(JSON, default=list) # e.g. ["weather-mcp"]
    training_data = Column(JSON, default=list) # e.g. [{"q": "...", "a": "..."}]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    hub = relationship("HubModel", back_populates="agents")
    parent = relationship("AgentModel", remote_side="AgentModel.id", back_populates="sub_agents")
    sub_agents = relationship("AgentModel", back_populates="parent")

class McpServerModel(Base):
    """Configured Model Context Protocol (MCP) server endpoints."""
    __tablename__ = "mcp_servers"
    id = Column(String, primary_key=True) # e.g. "github-mcp"
    name = Column(String, nullable=False)
    type = Column(String, default="stdio") # "stdio" or "sse"
    command = Column(String, nullable=True) # e.g. "npx" or "docker" for stdio
    args = Column(JSON, default=list) # e.g. ["-y", "@modelcontextprotocol/server-github"]
    url = Column(String, nullable=True) # HTTP/SSE endpoint for sse type
    env = Column(JSON, default=dict) # Environment variables (tokens, paths)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessageModel(Base):
    """Enriched chat messages capturing token consumption details."""
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(String, nullable=False) # 'human', 'ai', 'system'
    content = Column(Text, nullable=False)
    
    # Token usage logging
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class PerformanceLogModel(Base):
    """Performance metrics including token usage leaderboard data."""
    __tablename__ = "performance_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    ttft = Column(Float, nullable=False)
    total_time = Column(Float, nullable=False)
    
    # Token usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class WorkflowModel(Base):
    """Stores visual execution graphs/pipelines of agents."""
    __tablename__ = "workflows"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    nodes = Column(JSON, default=list) # React Flow node configurations
    edges = Column(JSON, default=list) # React Flow connection details
    created_at = Column(DateTime, default=datetime.utcnow)

class ScheduledTaskModel(Base):
    """Stores scheduled/looped tasks that the agent executes on a timer."""
    __tablename__ = "scheduled_tasks"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    interval_minutes = Column(Integer, nullable=True)  # None = one-time task
    run_at = Column(DateTime, nullable=False, index=True)  # Next scheduled execution time
    last_run = Column(DateTime, nullable=True)  # Last execution timestamp
    status = Column(String, default="active", index=True)  # active, paused, completed, running
    history = Column(JSON, default=list)  # List of {timestamp, status, summary}
    created_at = Column(DateTime, default=datetime.utcnow)

Index('idx_scheduled_tasks_status_run_at', ScheduledTaskModel.status, ScheduledTaskModel.run_at)
