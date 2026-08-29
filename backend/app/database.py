"""
Database engine & session management (SQLAlchemy).

Works out of the box with SQLite for local development and demos, and
transparently supports PostgreSQL (or any SQLAlchemy-compatible DB) by
changing DATABASE_URL — no code changes required.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and guarantees closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once at application startup."""
    # Import models here so they are registered on Base before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
