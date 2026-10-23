import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "senior-agent-secret-key-2026-secure")

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = secrets.token_hex(16)
    iterations = 100000
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${derived}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plain password against the stored PBKDF2 hash."""
    try:
        parts = stored_hash.split('$')
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_derived = parts[3]
        actual_derived = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        ).hex()
        return hmac.compare_digest(actual_derived, expected_derived)
    except Exception:
        return False

def generate_auth_token(user_id: str, username: str) -> str:
    """Generate a signed bearer token containing user identity and expiration."""
    expires_at = int(time.time()) + (86400 * 30) # 30 days
    payload = f"{user_id}:{username}:{expires_at}"
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    # Format: user_id.username.expires_at.signature
    return f"{user_id}.{username}.{expires_at}.{signature}"

def verify_auth_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate a bearer token and return user identity if valid."""
    try:
        parts = token.split('.')
        if len(parts) != 4:
            return None
        user_id, username, expires_at_str, signature = parts
        expires_at = int(expires_at_str)
        if time.time() > expires_at:
            return None # Expired
        
        payload = f"{user_id}:{username}:{expires_at_str}"
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(signature, expected_sig):
            return {"user_id": user_id, "username": username}
        return None
    except Exception:
        return None

# --- Pydantic Schemas ---

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=4)
    full_name: Optional[str] = None
    role: Optional[str] = "user"

class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    storage_type: str = "mongodb"

class AuthResponse(BaseModel):
    status: str = "success"
    token: str
    user: UserResponse
    mongo_connected: bool = False

class MongoStatusResponse(BaseModel):
    connected: bool
    status: str
    url: str
    database: str
    latency_ms: float
    collections: List[str] = []
    counts: Dict[str, int] = {}
    error: Optional[str] = None
    message: Optional[str] = None

class MongoConnectRequest(BaseModel):
    url: str
    database: Optional[str] = "senior_agent"
