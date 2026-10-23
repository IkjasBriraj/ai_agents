import os
import re
import time
import logging
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/senior_agent")
DB_NAME = os.environ.get("MONGODB_DB_NAME", "senior_agent")

_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db: Optional[AsyncIOMotorDatabase] = None

# Smart connection cache to prevent repeated 2s timeouts when offline
_last_check_time: float = 0.0
_cached_connected: bool = False
_cooldown_period: float = 10.0 # Re-check connection at most every 10s when offline

def sanitize_mongo_url(url: str) -> str:
    """Mask credentials in MongoDB connection string for safe display."""
    if not url:
        return ""
    return re.sub(r":([^/@]+)@", ":****@", url)

def is_mongodb_enabled() -> bool:
    """Check if MongoDB mode is explicitly enabled or requested via environment."""
    return os.environ.get("USE_MONGODB", "false").lower() in ("true", "1", "yes") or "MONGODB_URL" in os.environ

def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client, MONGODB_URL
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
            socketTimeoutMS=1500
        )
    return _mongo_client

def get_mongo_db() -> AsyncIOMotorDatabase:
    global _mongo_db, DB_NAME
    if _mongo_db is None:
        client = get_mongo_client()
        _mongo_db = client[DB_NAME]
    return _mongo_db

async def set_mongo_url(new_url: str, new_db_name: Optional[str] = None):
    """Dynamically switch MongoDB connection string and reconnect."""
    global _mongo_client, _mongo_db, MONGODB_URL, DB_NAME, _last_check_time, _cached_connected
    await close_mongo_db()
    MONGODB_URL = new_url
    if new_db_name:
        DB_NAME = new_db_name
    os.environ["MONGODB_URL"] = new_url
    os.environ["USE_MONGODB"] = "true"
    _last_check_time = 0.0 # Force re-check
    await check_mongo_connection()
    await init_mongo_db()

async def check_mongo_connection(timeout_ms: int = 1500) -> Dict[str, Any]:
    """Test connection to MongoDB and return diagnostics."""
    global _last_check_time, _cached_connected
    client = get_mongo_client()
    start = time.time()
    try:
        # Ping admin database
        await client.admin.command('ping')
        latency_ms = round((time.time() - start) * 1000, 2)
        db = get_mongo_db()
        collection_names = await db.list_collection_names()
        
        user_count = await db.users.count_documents({}) if "users" in collection_names else 0
        message_count = await db.chat_messages.count_documents({}) if "chat_messages" in collection_names else 0
        agent_count = await db.agents.count_documents({}) if "agents" in collection_names else 0

        _cached_connected = True
        _last_check_time = time.time()

        return {
            "connected": True,
            "status": "healthy",
            "url": sanitize_mongo_url(MONGODB_URL),
            "database": DB_NAME,
            "latency_ms": latency_ms,
            "collections": collection_names,
            "counts": {
                "users": user_count,
                "chat_messages": message_count,
                "agents": agent_count
            }
        }
    except Exception as e:
        latency_ms = round((time.time() - start) * 1000, 2)
        _cached_connected = False
        _last_check_time = time.time()
        return {
            "connected": False,
            "status": "disconnected",
            "url": sanitize_mongo_url(MONGODB_URL),
            "database": DB_NAME,
            "latency_ms": latency_ms,
            "error": str(e),
            "message": "MongoDB is not reachable at configured URL. Using local SQLite store as fallback."
        }

def should_attempt_mongo() -> bool:
    """Return True if Mongo is connected or ready to be re-tested."""
    global _cached_connected, _last_check_time
    if _cached_connected:
        return True
    return (time.time() - _last_check_time) > _cooldown_period

async def init_mongo_db():
    """Initialize MongoDB collections and create performance indexes."""
    global _cached_connected
    if not should_attempt_mongo():
        return
    try:
        db = get_mongo_db()
        await db.command('ping')
        _cached_connected = True
        
        await db.chat_messages.create_index([("session_id", 1), ("timestamp", -1)])
        await db.chat_messages.create_index([("agent_id", 1)])
        await db.performance_logs.create_index([("agent_id", 1), ("timestamp", -1)])
        await db.scheduled_tasks.create_index([("status", 1), ("run_at", 1)])
        await db.hubs.create_index([("id", 1)], unique=True)
        await db.agents.create_index([("id", 1)], unique=True)
        await db.mcp_servers.create_index([("id", 1)], unique=True)
        await db.workflows.create_index([("id", 1)], unique=True)

        await db.users.create_index([("username", 1)], unique=True)
        await db.users.create_index([("email", 1)], unique=True)
        await db.users.create_index([("id", 1)], unique=True)

        logger.info("MongoDB collections and indexes initialized successfully at %s", sanitize_mongo_url(MONGODB_URL))
    except Exception as e:
        _cached_connected = False
        logger.warning("MongoDB initialization note (offline or standby): %s", e)

async def close_mongo_db():
    global _mongo_client, _mongo_db, _cached_connected
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        _cached_connected = False

async def mongo_create_user(user_doc: Dict[str, Any]) -> bool:
    if not should_attempt_mongo():
        return False
    try:
        db = get_mongo_db()
        await db.users.insert_one(user_doc)
        return True
    except Exception as e:
        logger.warning("Could not persist user to MongoDB: %s", e)
        return False

async def mongo_get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    if not should_attempt_mongo():
        return None
    try:
        db = get_mongo_db()
        return await db.users.find_one({"username": username}, {"_id": 0})
    except Exception as e:
        logger.warning("Could not fetch user by username from MongoDB: %s", e)
        return None

async def mongo_get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    if not should_attempt_mongo():
        return None
    try:
        db = get_mongo_db()
        return await db.users.find_one({"email": email.lower()}, {"_id": 0})
    except Exception as e:
        logger.warning("Could not fetch user by email from MongoDB: %s", e)
        return None

async def mongo_get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    if not should_attempt_mongo():
        return None
    try:
        db = get_mongo_db()
        return await db.users.find_one({"id": user_id}, {"_id": 0})
    except Exception as e:
        logger.warning("Could not fetch user by id from MongoDB: %s", e)
        return None

async def mongo_update_user(user_id: str, updates: Dict[str, Any]) -> bool:
    if not should_attempt_mongo():
        return False
    try:
        db = get_mongo_db()
        result = await db.users.update_one({"id": user_id}, {"$set": updates})
        return result.modified_count > 0
    except Exception as e:
        logger.warning("Could not update user in MongoDB: %s", e)
        return False
