import bcrypt
import os
import secrets
from typing import Optional
from fastapi import Request
from .config import PASSWORD_FILE
from starlette.responses import RedirectResponse

# --- Authentication ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def init_admin_password():
    """Initialize admin password if it doesn't exist"""
    if not os.path.exists(PASSWORD_FILE):
        # Create password file with default password
        hashed_pw = hash_password("admin_password")  # Change this in production
        with open(PASSWORD_FILE, "w") as f:
            f.write(hashed_pw)
        return hashed_pw
    else:
        # Read existing password
        with open(PASSWORD_FILE, "r") as f:
            return f.read().strip()

# In-memory session storage (for demonstration)
# In production, use a proper session store like Redis
user_sessions = {}

def create_session(user_id: str) -> str:
    """Create a new session and return session ID"""
    session_id = secrets.token_urlsafe(32)
    user_sessions[session_id] = user_id
    return session_id

def get_session_user(session_id: str) -> Optional[str]:
    """Get user ID from session ID"""
    return user_sessions.get(session_id)

def delete_session(session_id: str):
    """Delete session"""
    if session_id in user_sessions:
        del user_sessions[session_id]

def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated"""
    session_id = request.cookies.get("session_id")
    return session_id is not None and get_session_user(session_id) is not None

async def auth_middleware(request: Request, call_next):
    if request.url.path in ['/login', '/logout'] or request.url.path.startswith('/_nicegui/'):
        return await call_next(request)
    
    if not is_authenticated(request):
        return RedirectResponse(url='/login', status_code=302)
    
    return await call_next(request)