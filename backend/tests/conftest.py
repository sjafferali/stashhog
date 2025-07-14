"""Shared pytest fixtures and configuration."""
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app


@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Return test database URL."""
    return "sqlite:///:memory:"


@pytest.fixture
def anyio_backend():
    """Configure anyio for pytest-asyncio."""
    return "asyncio"