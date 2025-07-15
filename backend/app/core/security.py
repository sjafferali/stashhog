"""
Security utilities for the application.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return str(pwd_context.hash(password))


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, settings.security.secret_key, algorithm=settings.security.algorithm
    )

    return str(encoded_jwt)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT access token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token data or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm],
        )
        return dict(payload)
    except (InvalidTokenError, ValueError):
        return None


def verify_api_key(api_key: str) -> bool:
    """
    Verify an API key.

    This is a placeholder for API key verification.
    In a real implementation, you would check against a database.

    Args:
        api_key: API key to verify

    Returns:
        True if API key is valid
    """
    # TODO: Implement actual API key verification
    # For now, just check if it's not empty
    return bool(api_key and len(api_key) > 10)


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}

    def is_allowed(self, key: str) -> bool:
        """
        Check if a request is allowed.

        Args:
            key: Unique key for rate limiting (e.g., IP address, user ID)

        Returns:
            True if request is allowed
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key] if req_time > window_start
            ]
        else:
            self.requests[key] = []

        # Check if allowed
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True

        return False

    def get_reset_time(self, key: str) -> Optional[datetime]:
        """
        Get the time when rate limit resets.

        Args:
            key: Unique key for rate limiting

        Returns:
            Reset time or None if no requests
        """
        if key not in self.requests or not self.requests[key]:
            return None

        oldest_request = min(self.requests[key])
        return datetime(
            oldest_request.year,
            oldest_request.month,
            oldest_request.day,
            oldest_request.hour,
            oldest_request.minute,
            oldest_request.second,
            oldest_request.microsecond,
        ) + timedelta(seconds=self.window_seconds)


# Global rate limiter instance
rate_limiter = RateLimiter()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re

    # Remove any path components
    filename = filename.replace("/", "").replace("\\", "")

    # Remove special characters except dots and hyphens
    filename = re.sub(r"[^\w\s.-]", "", filename)

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + "." + ext if ext else name[:255]

    return filename


def validate_url(url: str) -> bool:
    """
    Validate that a URL is safe to use.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid and safe
    """
    from urllib.parse import urlparse

    try:
        result = urlparse(url)

        # Check scheme
        if result.scheme not in ["http", "https"]:
            return False

        # Check for localhost/private IPs (security consideration)
        hostname = result.hostname
        if hostname:
            # Block localhost and common private IP patterns
            blocked_hosts = [
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
                "::1",
            ]

            if hostname in blocked_hosts:
                return False

            # Check for private IP ranges
            if hostname.startswith(
                (
                    "10.",
                    "172.16.",
                    "172.17.",
                    "172.18.",
                    "172.19.",
                    "172.20.",
                    "172.21.",
                    "172.22.",
                    "172.23.",
                    "172.24.",
                    "172.25.",
                    "172.26.",
                    "172.27.",
                    "172.28.",
                    "172.29.",
                    "172.30.",
                    "172.31.",
                    "192.168.",
                )
            ):
                return False

        return True
    except Exception:
        return False
