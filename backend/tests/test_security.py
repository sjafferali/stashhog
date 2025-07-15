"""Tests for security utilities."""

from datetime import datetime, timedelta
from unittest.mock import patch

import jwt

from app.core.security import (
    RateLimiter,
    create_access_token,
    decode_access_token,
    get_password_hash,
    rate_limiter,
    sanitize_filename,
    validate_url,
    verify_api_key,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_get_password_hash(self):
        """Test password hashing."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes."""
        password = "mysecretpassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Due to salt


class TestJWT:
    """Test JWT token functions."""

    @patch("app.core.security.settings")
    def test_create_access_token_default_expiry(self, mock_settings):
        """Test creating access token with default expiry."""
        mock_settings.security.secret_key = "test-secret"
        mock_settings.security.algorithm = "HS256"
        mock_settings.security.access_token_expire_minutes = 30

        data = {"sub": "user123", "scopes": ["read"]}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode to verify
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["sub"] == "user123"
        assert decoded["scopes"] == ["read"]
        assert "exp" in decoded

    @patch("app.core.security.settings")
    def test_create_access_token_custom_expiry(self, mock_settings):
        """Test creating access token with custom expiry."""
        mock_settings.security.secret_key = "test-secret"
        mock_settings.security.algorithm = "HS256"

        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta)

        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])

        # Check expiry is approximately 60 minutes from now
        exp_time = datetime.utcfromtimestamp(decoded["exp"])
        expected_exp = datetime.utcnow() + timedelta(minutes=60)
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    @patch("app.core.security.settings")
    def test_decode_access_token_valid(self, mock_settings):
        """Test decoding valid access token."""
        mock_settings.security.secret_key = "test-secret"
        mock_settings.security.algorithm = "HS256"

        # Create a valid token
        data = {"sub": "user123", "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(data, "test-secret", algorithm="HS256")

        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user123"

    @patch("app.core.security.settings")
    def test_decode_access_token_invalid(self, mock_settings):
        """Test decoding invalid access token."""
        mock_settings.security.secret_key = "test-secret"
        mock_settings.security.algorithm = "HS256"

        # Invalid token
        decoded = decode_access_token("invalid.token.here")
        assert decoded is None

    @patch("app.core.security.settings")
    def test_decode_access_token_expired(self, mock_settings):
        """Test decoding expired access token."""
        mock_settings.security.secret_key = "test-secret"
        mock_settings.security.algorithm = "HS256"

        # Create an expired token
        data = {"sub": "user123", "exp": datetime.utcnow() - timedelta(hours=1)}
        token = jwt.encode(data, "test-secret", algorithm="HS256")

        decoded = decode_access_token(token)
        assert decoded is None


class TestAPIKey:
    """Test API key verification."""

    def test_verify_api_key_valid(self):
        """Test verifying valid API key."""
        # Currently just checks length > 10
        assert verify_api_key("12345678901") is True
        assert verify_api_key("verylongapikey123456") is True

    def test_verify_api_key_invalid(self):
        """Test verifying invalid API key."""
        assert verify_api_key("") is False
        assert verify_api_key("short") is False
        assert verify_api_key("1234567890") is False  # Exactly 10


class TestRateLimiter:
    """Test rate limiter functionality."""

    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_requests=50, window_seconds=30)

        assert limiter.max_requests == 50
        assert limiter.window_seconds == 30
        assert limiter.requests == {}

    def test_is_allowed_under_limit(self):
        """Test requests under rate limit."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True

    def test_is_allowed_over_limit(self):
        """Test requests over rate limit."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False  # Over limit

    def test_is_allowed_different_keys(self):
        """Test rate limiting with different keys."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user2") is True  # Different key
        assert limiter.is_allowed("user1") is False  # user1 over limit
        assert limiter.is_allowed("user2") is False  # user2 over limit

    @patch("app.core.security.datetime")
    def test_is_allowed_window_expiry(self, mock_datetime):
        """Test rate limit window expiry."""
        # Setup time mocking
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = base_time

        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # First request
        assert limiter.is_allowed("user1") is True

        # Second request immediately - should fail
        assert limiter.is_allowed("user1") is False

        # Move time forward past window
        mock_datetime.utcnow.return_value = base_time + timedelta(seconds=61)

        # Should be allowed again
        assert limiter.is_allowed("user1") is True

    def test_get_reset_time(self):
        """Test getting rate limit reset time."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # No requests yet
        assert limiter.get_reset_time("user1") is None

        # Make a request
        limiter.is_allowed("user1")
        reset_time = limiter.get_reset_time("user1")

        assert reset_time is not None
        assert isinstance(reset_time, datetime)

    def test_global_rate_limiter(self):
        """Test the global rate limiter instance."""
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)


class TestUtilities:
    """Test utility functions."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        assert sanitize_filename("normal-file.txt") == "normal-file.txt"
        assert sanitize_filename("file with spaces.pdf") == "file with spaces.pdf"

    def test_sanitize_filename_path_traversal(self):
        """Test preventing path traversal."""
        # Dots are allowed in filenames
        assert sanitize_filename("../../../etc/passwd") == "......etcpasswd"
        assert (
            sanitize_filename("..\\windows\\system32\\file.dll")
            == "..windowssystem32file.dll"
        )

    def test_sanitize_filename_special_chars(self):
        """Test removing special characters."""
        assert sanitize_filename("file@#$%.txt") == "file.txt"
        assert sanitize_filename("script<>|.js") == "script.js"

    def test_sanitize_filename_length_limit(self):
        """Test filename length limiting."""
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name)

        assert len(sanitized) <= 255
        assert sanitized.endswith(".txt")

    def test_sanitize_filename_no_extension(self):
        """Test sanitizing filename without extension."""
        long_name = "b" * 300
        sanitized = sanitize_filename(long_name)

        assert len(sanitized) <= 255

    def test_validate_url_valid(self):
        """Test validating valid URLs."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://test.org/path") is True
        assert validate_url("https://api.service.com:8080/v1/endpoint") is True

    def test_validate_url_invalid_scheme(self):
        """Test rejecting invalid schemes."""
        assert validate_url("ftp://example.com") is False
        assert validate_url("file:///etc/passwd") is False
        assert validate_url("javascript:alert(1)") is False

    def test_validate_url_localhost(self):
        """Test rejecting localhost URLs."""
        assert validate_url("http://localhost/api") is False
        assert validate_url("https://127.0.0.1:8000") is False
        assert validate_url("http://[::1]/test") is False
        assert validate_url("http://0.0.0.0") is False

    def test_validate_url_private_ips(self):
        """Test rejecting private IP ranges."""
        assert validate_url("http://10.0.0.1") is False
        assert validate_url("http://192.168.1.1") is False
        assert validate_url("http://172.16.0.1") is False
        assert validate_url("http://172.31.255.255") is False

    def test_validate_url_malformed(self):
        """Test handling malformed URLs."""
        assert validate_url("not a url") is False
        assert validate_url("") is False
        assert validate_url("ht!tp://bad-url") is False
