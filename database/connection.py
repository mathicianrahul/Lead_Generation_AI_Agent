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
    """Initializes all database tables and ensures schema migrations."""
    try:
        from database import models  # Ensure all models are registered
        Base.metadata.create_all(bind=engine)

        # Non-destructive auto-migration for newly added columns
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "leads" in inspector.get_table_names():
            existing_cols = [c["name"] for c in inspector.get_columns("leads")]
            if "source" not in existing_cols:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE leads ADD COLUMN source VARCHAR(100) DEFAULT 'Google Places API'"))
                    conn.commit()
                logger.info("Auto-migrated 'leads' table: added 'source' column.")

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


