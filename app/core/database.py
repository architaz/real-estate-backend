"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create database engine
# pool_pre_ping=True checks connections before using them (handles disconnects)
# echo=True logs all SQL queries (useful for debugging)
engine = create_engine(
    settings.database_url.replace("mysql://", "mysql+pymysql://"),
    pool_pre_ping=True,
    echo=settings.debug,
    pool_size=5,          # Connection pool size
    max_overflow=10       # Extra connections if pool is full
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,  # Transactions must be explicitly committed
    autoflush=False,   # Don't auto-flush changes
    bind=engine
)


def get_db() -> Session:
    """
    Dependency function for FastAPI routes.
    Provides a database session and ensures it's closed after use.
    
    Usage in routes:
        @router.get("/properties")
        def list_properties(db: Session = Depends(get_db)):
            # Use db here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Call this on application startup.
    """
    from app.models.property import Base
    from app.models.amenity import Amenity 
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")