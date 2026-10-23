import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Header, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from database.db import get_db
from database.models import UserModel
from database.mongo_db import (
    check_mongo_connection,
    set_mongo_url,
    mongo_create_user,
    mongo_get_user_by_username,
    mongo_get_user_by_email,
    mongo_get_user_by_id,
    mongo_update_user,
    is_mongodb_enabled
)
from database.auth_models import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    AuthResponse,
    MongoStatusResponse,
    MongoConnectRequest,
    hash_password,
    verify_password,
    generate_auth_token,
    verify_auth_token
)

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
database_router = APIRouter(prefix="/api/database", tags=["database"])

async def get_current_user_from_token(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Dependency to validate bearer token and return user profile."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    token = authorization.split("Bearer ", 1)[1].strip()
    payload = verify_auth_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload["user_id"]
    
    # Check MongoDB first
    mongo_user = await mongo_get_user_by_id(user_id)
    if mongo_user:
        return UserResponse(
            id=mongo_user["id"],
            username=mongo_user["username"],
            email=mongo_user["email"],
            full_name=mongo_user.get("full_name"),
            role=mongo_user.get("role", "user"),
            created_at=str(mongo_user.get("created_at")),
            last_login=str(mongo_user.get("last_login")),
            storage_type="mongodb"
        )
    
    # Fallback to SQLite
    result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
    sqlite_user = result.scalar_one_or_none()
    if sqlite_user:
        return UserResponse(
            id=sqlite_user.id,
            username=sqlite_user.username,
            email=sqlite_user.email,
            full_name=sqlite_user.full_name,
            role=sqlite_user.role,
            created_at=sqlite_user.created_at.isoformat() if sqlite_user.created_at else None,
            last_login=sqlite_user.last_login.isoformat() if sqlite_user.last_login else None,
            storage_type="sqlite"
        )
        
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@auth_router.post("/register", response_model=AuthResponse)
async def register(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user in MongoDB and SQLite."""
    username_clean = request.username.strip().lower()
    email_clean = request.email.strip().lower()
    
    # 1. Check if user exists in SQLite
    sqlite_exist = await db.execute(
        select(UserModel).filter(
            or_(UserModel.username == username_clean, UserModel.email == email_clean)
        )
    )
    if sqlite_exist.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already registered")
        
    # 2. Check if user exists in MongoDB
    if await mongo_get_user_by_username(username_clean) or await mongo_get_user_by_email(email_clean):
        raise HTTPException(status_code=400, detail="Username or email already registered in MongoDB")

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    hashed_pwd = hash_password(request.password)
    now = datetime.now(timezone.utc)
    
    # 3. Store in SQLite
    sqlite_user = UserModel(
        id=user_id,
        username=username_clean,
        email=email_clean,
        password_hash=hashed_pwd,
        full_name=request.full_name or request.username,
        role=request.role or "user",
        created_at=now,
        last_login=now
    )
    db.add(sqlite_user)
    await db.commit()
    
    # 4. Store in MongoDB
    mongo_doc = {
        "id": user_id,
        "username": username_clean,
        "email": email_clean,
        "password_hash": hashed_pwd,
        "full_name": request.full_name or request.username,
        "role": request.role or "user",
        "created_at": now.isoformat(),
        "last_login": now.isoformat(),
    }
    mongo_saved = await mongo_create_user(mongo_doc)
    
    token = generate_auth_token(user_id, username_clean)
    
    return AuthResponse(
        status="success",
        token=token,
        user=UserResponse(
            id=user_id,
            username=username_clean,
            email=email_clean,
            full_name=request.full_name or request.username,
            role=request.role or "user",
            created_at=now.isoformat(),
            last_login=now.isoformat(),
            storage_type="mongodb" if mongo_saved else "sqlite"
        ),
        mongo_connected=mongo_saved
    )


@auth_router.post("/login", response_model=AuthResponse)
async def login(request: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user with username/email and password."""
    identifier = request.username_or_email.strip().lower()
    user_id = None
    stored_hash = None
    user_dict = None
    used_mongo = False
    
    # 1. Try MongoDB lookup
    mongo_user = await mongo_get_user_by_username(identifier)
    if not mongo_user and "@" in identifier:
        mongo_user = await mongo_get_user_by_email(identifier)
        
    if mongo_user:
        user_id = mongo_user["id"]
        stored_hash = mongo_user.get("password_hash")
        user_dict = mongo_user
        used_mongo = True
    else:
        # 2. Try SQLite lookup
        result = await db.execute(
            select(UserModel).filter(
                or_(UserModel.username == identifier, UserModel.email == identifier)
            )
        )
        sqlite_user = result.scalar_one_or_none()
        if sqlite_user:
            user_id = sqlite_user.id
            stored_hash = sqlite_user.password_hash
            user_dict = {
                "id": sqlite_user.id,
                "username": sqlite_user.username,
                "email": sqlite_user.email,
                "full_name": sqlite_user.full_name,
                "role": sqlite_user.role,
                "created_at": sqlite_user.created_at.isoformat() if sqlite_user.created_at else None,
                "last_login": sqlite_user.last_login.isoformat() if sqlite_user.last_login else None
            }

    if not user_dict or not stored_hash or not verify_password(request.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password"
        )

    # Update last login
    now_iso = datetime.now(timezone.utc).isoformat()
    if used_mongo:
        await mongo_update_user(user_id, {"last_login": now_iso})
    else:
        # Update SQLite
        res = await db.execute(select(UserModel).filter(UserModel.id == user_id))
        su = res.scalar_one_or_none()
        if su:
            su.last_login = datetime.now(timezone.utc)
            await db.commit()

    token = generate_auth_token(user_id, user_dict["username"])
    
    # Check if MongoDB is currently connected
    mongo_diag = await check_mongo_connection()

    return AuthResponse(
        status="success",
        token=token,
        user=UserResponse(
            id=user_dict["id"],
            username=user_dict["username"],
            email=user_dict["email"],
            full_name=user_dict.get("full_name"),
            role=user_dict.get("role", "user"),
            created_at=str(user_dict.get("created_at")),
            last_login=now_iso,
            storage_type="mongodb" if mongo_diag.get("connected") else "sqlite"
        ),
        mongo_connected=mongo_diag.get("connected", False)
    )


@auth_router.post("/demo", response_model=AuthResponse)
async def demo_login(db: AsyncSession = Depends(get_db)):
    """One-click instant login for guests / demo evaluations."""
    demo_id = "usr_guest_demo"
    demo_username = "guest_researcher"
    demo_email = "guest@senioragent.local"
    
    # Check if demo user exists in SQLite
    result = await db.execute(select(UserModel).filter(UserModel.id == demo_id))
    user = result.scalar_one_or_none()
    
    now = datetime.now(timezone.utc)
    if not user:
        demo_pwd_hash = hash_password("demo_guest_access_2026")
        user = UserModel(
            id=demo_id,
            username=demo_username,
            email=demo_email,
            password_hash=demo_pwd_hash,
            full_name="Guest Researcher",
            role="lead_architect",
            created_at=now,
            last_login=now
        )
        db.add(user)
        await db.commit()
        
        # Also store in Mongo if available
        await mongo_create_user({
            "id": demo_id,
            "username": demo_username,
            "email": demo_email,
            "password_hash": demo_pwd_hash,
            "full_name": "Guest Researcher",
            "role": "lead_architect",
            "created_at": now.isoformat(),
            "last_login": now.isoformat(),
        })
    else:
        user.last_login = now
        await db.commit()
        await mongo_update_user(demo_id, {"last_login": now.isoformat()})

    token = generate_auth_token(demo_id, demo_username)
    mongo_diag = await check_mongo_connection()

    return AuthResponse(
        status="success",
        token=token,
        user=UserResponse(
            id=demo_id,
            username=demo_username,
            email=demo_email,
            full_name="Guest Researcher",
            role="lead_architect",
            created_at=user.created_at.isoformat() if user.created_at else now.isoformat(),
            last_login=now.isoformat(),
            storage_type="mongodb" if mongo_diag.get("connected") else "sqlite"
        ),
        mongo_connected=mongo_diag.get("connected", False)
    )


@auth_router.get("/me", response_model=UserResponse)
async def get_me(user: UserResponse = Depends(get_current_user_from_token)):
    """Get the currently logged-in user's profile."""
    return user


# --- MongoDB Database Status & Reconnect Endpoints ---

@database_router.get("/status", response_model=MongoStatusResponse)
async def get_database_status():
    """Diagnostic check for MongoDB connection, latency, and collection stats."""
    diag = await check_mongo_connection()
    return MongoStatusResponse(
        connected=diag.get("connected", False),
        status=diag.get("status", "unknown"),
        url=diag.get("url", ""),
        database=diag.get("database", "senior_agent"),
        latency_ms=diag.get("latency_ms", 0.0),
        collections=diag.get("collections", []),
        counts=diag.get("counts", {}),
        error=diag.get("error"),
        message=diag.get("message")
    )


@database_router.post("/connect", response_model=MongoStatusResponse)
async def connect_database(req: MongoConnectRequest):
    """Dynamically configure and connect to a MongoDB instance (e.g. Atlas or local)."""
    if not req.url:
        raise HTTPException(status_code=400, detail="MongoDB URL cannot be empty")
    
    await set_mongo_url(req.url, req.database)
    diag = await check_mongo_connection()
    
    return MongoStatusResponse(
        connected=diag.get("connected", False),
        status=diag.get("status", "unknown"),
        url=diag.get("url", ""),
        database=diag.get("database", req.database or "senior_agent"),
        latency_ms=diag.get("latency_ms", 0.0),
        collections=diag.get("collections", []),
        counts=diag.get("counts", {}),
        error=diag.get("error"),
        message="Connected successfully to MongoDB!" if diag.get("connected") else diag.get("error")
    )
