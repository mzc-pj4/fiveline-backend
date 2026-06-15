"""
pytest conftest for product-service.

Sets required environment variables BEFORE any app module is imported.
This must happen at the conftest level (earliest collection phase) so that
pydantic-settings can read them when `Settings()` is instantiated at module scope.
"""
import os

# Set env vars before any app imports occur
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
