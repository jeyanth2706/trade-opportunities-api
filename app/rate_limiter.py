import logging
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter using sliding window algorithm"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
    
    def is_allowed(self, session_id: str) -> bool:
        """
        Check if a request is allowed for the given session_id.
        Uses sliding window algorithm.
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Get requests for this session
        if session_id not in self.requests:
            self.requests[session_id] = []
        
        # Remove old requests outside the window
        self.requests[session_id] = [
            req_time for req_time in self.requests[session_id]
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.requests[session_id]) >= self.max_requests:
            logger.warning(
                f"⚠️ Rate limit exceeded for session {session_id}: "
                f"{len(self.requests[session_id])}/{self.max_requests} requests"
            )
            return False
        
        # Add current request
        self.requests[session_id].append(now)
        logger.info(
            f"✓ Request allowed for session {session_id}: "
            f"{len(self.requests[session_id])}/{self.max_requests}"
        )
        return True
    
    def get_remaining_requests(self, session_id: str) -> int:
        """Get remaining requests for the session"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        if session_id not in self.requests:
            return self.max_requests
        
        # Count requests in current window
        active_requests = len([
            req_time for req_time in self.requests[session_id]
            if req_time > window_start
        ])
        
        return max(0, self.max_requests - active_requests)
    
    def reset_session(self, session_id: str):
        """Reset rate limit for a session"""
        if session_id in self.requests:
            del self.requests[session_id]
            logger.info(f"✓ Rate limit reset for session {session_id}")