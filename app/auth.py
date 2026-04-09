import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import Depends, HTTPException, Request

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions with automatic expiry"""
    
    def __init__(self, session_timeout_hours: int = 24):
        self.sessions: Dict[str, dict] = {}
        self.session_timeout = timedelta(hours=session_timeout_hours)
    
    def create_session(self) -> str:
        """Create a new session and return session ID"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.now(),
            "last_accessed": datetime.now(),
            "request_count": 0
        }
        logger.info(f"✓ Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session if it exists and is not expired"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is expired
        if datetime.now() - session["last_accessed"] > self.session_timeout:
            del self.sessions[session_id]
            logger.info(f"✓ Expired session: {session_id}")
            return None
        
        # Update last accessed time
        session["last_accessed"] = datetime.now()
        session["request_count"] += 1
        
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"✓ Deleted session: {session_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        expired = []
        for session_id, session in self.sessions.items():
            if datetime.now() - session["last_accessed"] > self.session_timeout:
                expired.append(session_id)
        
        for session_id in expired:
            del self.sessions[session_id]
        
        if expired:
            logger.info(f"✓ Cleaned up {len(expired)} expired sessions")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def get_or_create_session(request: Request) -> dict:
    """
    Dependency that gets or creates a session.
    Extracts session_id from query params or headers, or creates new one.
    """
    session_manager = get_session_manager()
    
    # Try to get session_id from query parameters or headers
    session_id = request.query_params.get("session_id")
    
    if not session_id:
        session_id = request.headers.get("X-Session-ID")
    
    # Get existing session or create new one
    if session_id:
        session = session_manager.get_session(session_id)
        if session:
            logger.info(f"✓ Using existing session: {session_id}")
            return session
    
    # Create new session if not found or expired
    new_session_id = session_manager.create_session()
    return session_manager.get_session(new_session_id)