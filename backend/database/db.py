from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os

if os.environ.get("TESTING") == "true":
    DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_agent.db"))
else:
    DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "senior_agent.db"))

ASYNC_DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
SYNC_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

from sqlalchemy import event

# Async components for async routing and tasks
async_engine = create_async_engine(
    ASYNC_DATABASE_URL, 
    echo=False, 
    connect_args={"timeout": 30}
)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync components for sync tasks/callbacks
sync_engine = create_engine(
    SYNC_DATABASE_URL, 
    echo=False, 
    connect_args={"check_same_thread": False, "timeout": 30}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

@event.listens_for(async_engine.sync_engine, "connect")
def set_async_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

# Create tables synchronously on module import to ensure tables always exist
from .models import Base
try:
    Base.metadata.create_all(sync_engine)
except Exception as e:
    print(f"Database table auto-creation error: {e}")

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Dependency to get db session in FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_sync_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
