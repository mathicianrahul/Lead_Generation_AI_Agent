from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from config.settings import settings
from config.logging_config import logger

Base = declarative_base()

# SQLite or PostgreSQL engine
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def init_db():
    """Initializes all database tables."""
    try:
        from database import models  # Ensure all models are registered
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully at %s", settings.database_url)
    except Exception as e:
        logger.error("Failed to initialize database: %s", str(e))
        raise


def get_db():
    """Context-friendly database session generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager for obtaining a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


