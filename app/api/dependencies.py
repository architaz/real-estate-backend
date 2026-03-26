"""
Shared dependencies for FastAPI routes.
"""
from app.core.database import get_db

# Re-export for convenience
__all__ = ["get_db"]