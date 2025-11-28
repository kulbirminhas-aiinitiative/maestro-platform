"""Pytest configuration and shared fixtures."""

import pytest
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing"""
    class MockCursor:
        def execute(self, query, params=None):
            pass

        def fetchall(self):
            return []

        def fetchone(self):
            return (0,)

        def close(self):
            pass

    class MockConnection:
        closed = False

        def cursor(self):
            return MockCursor()

        def close(self):
            self.closed = True

    return MockConnection()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    class MockRedis:
        def __init__(self):
            self._data = {}

        def ping(self):
            return True

        def get(self, key):
            return self._data.get(key)

        def set(self, key, value):
            self._data[key] = value

        def hgetall(self, key):
            return {}

        def lrange(self, key, start, end):
            return []

    return MockRedis()
