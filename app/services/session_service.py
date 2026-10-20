"""
Session management service for eCourts search workflows.
Maintains session cookies and CAPTCHA challenge states across requests with TTL expiration.
"""

import time
import uuid
import base64
import logging
import threading
from typing import Dict, Optional, Any
from app.config.settings import settings
from app.utils.exceptions import SessionExpiredException

log = logging.getLogger(__name__)


class SearchSession:
    """Represents a client state paired with an official eCourts HTTP session."""
    def __init__(
        self,
        session_id: str,
        cookies: Dict[str, str],
        captcha_image_bytes: bytes,
        ttl_seconds: int = 600,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        self.session_id = session_id
        self.cookies = cookies
        self.captcha_image_bytes = captcha_image_bytes
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.extra_data = extra_data or {}

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def time_remaining(self) -> int:
        return max(0, int(self.expires_at - time.time()))

    @property
    def captcha_data_uri(self) -> str:
        """Return base64 data URI suitable for rendering in an <img> tag."""
        b64 = base64.b64encode(self.captcha_image_bytes).decode("ascii")
        return f"data:image/png;base64,{b64}"


class SessionService:
    """Thread-safe in-memory session store."""
    def __init__(self):
        self._sessions: Dict[str, SearchSession] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        cookies: Dict[str, str],
        captcha_image_bytes: bytes,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> SearchSession:
        self.cleanup_expired()
        session_id = f"ec_{uuid.uuid4().hex}"
        session = SearchSession(
            session_id=session_id,
            cookies=cookies,
            captcha_image_bytes=captcha_image_bytes,
            ttl_seconds=settings.SESSION_TTL_SECONDS,
            extra_data=extra_data,
        )
        with self._lock:
            # Enforce maximum concurrent sessions
            if len(self._sessions) >= settings.MAX_ACTIVE_SESSIONS:
                # Evict oldest session
                oldest_key = min(self._sessions, key=lambda k: self._sessions[k].created_at)
                del self._sessions[oldest_key]
            self._sessions[session_id] = session

        log.info("Created search session %s (expires in %ds)", session_id, session.time_remaining)
        return session

    def get_session(self, session_id: str) -> SearchSession:
        """Retrieve active session or raise SessionExpiredException."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or session.is_expired:
                if session_id in self._sessions:
                    del self._sessions[session_id]
                raise SessionExpiredException()
            return session

    def remove_session(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def cleanup_expired(self) -> None:
        """Prune all expired sessions."""
        now = time.time()
        with self._lock:
            expired_keys = [k for k, v in self._sessions.items() if now > v.expires_at]
            for k in expired_keys:
                del self._sessions[k]

    @property
    def active_session_count(self) -> int:
        with self._lock:
            return len(self._sessions)


# Global singleton instance
session_service = SessionService()
