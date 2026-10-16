import os

import pytest

# The app refuses to start without a JWT secret. Give the tests a throwaway one.
# This value is only used by the test suite and protects nothing real.
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-used-anywhere-real-0123")


@pytest.fixture(autouse=True)
def fresh_database():
    """Give every test (in every test file) an empty database."""
    from database import Base
    from tests.test_api import engine

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)