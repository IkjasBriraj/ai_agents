import os
import logging
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/senior_agent")
DB_NAME = os.environ.get("MONGODB_DB_NAME", "senior_agent")

_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db: Optional[AsyncIOMotorDatabase] = None

def is_mongodb_enabled() -> bool:
    """Check if MongoDB mode is explicitly enabled or requested via environment."""
    return os.environ.get("USE_MONGODB", "false").lower() in ("true", "1", "yes") or "MONGODB_URL" in os.environ

def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGODB_URL)
    return _mongo_client

def get_mongo_db() -> AsyncIOMotorDatabase:
    global _mongo_db
    if _mongo_db is None:
        client = get_mongo_client()
        _mongo_db = client[DB_NAME]
    return _mongo_db

async def init_mongo_db():
    """Initialize MongoDB collections and create performance indexes."""
    try:
        db = get_mongo_db()
        # Create indexes for optimal query speeds
        await db.chat_messages.create_index([("session_id", 1), ("timestamp", -1)])
        await db.chat_messages.create_index([("agent_id", 1)])
        await db.performance_logs.create_index([("agent_id", 1), ("timestamp", -1)])
        await db.scheduled_tasks.create_index([("status", 1), ("run_at", 1)])
        await db.hubs.create_index([("id", 1)], unique=True)
        await db.agents.create_index([("id", 1)], unique=True)
        await db.mcp_servers.create_index([("id", 1)], unique=True)
        await db.workflows.create_index([("id", 1)], unique=True)
        logger.info("MongoDB collections and indexes initialized successfully at %s", MONGODB_URL)
    except Exception as e:
        logger.warning("MongoDB initialization warning: %s", e)

async def close_mongo_db():
    global _mongo_client, _mongo_db
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
