"""Database engine factory, connection lifecycle, and session management."""

from contextlib import contextmanager
import os
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base

DEFAULT_DATABASE_URL = "sqlite:///./data/sicra.db"


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints on SQLite connections."""
    url_str = ""
    if hasattr(connection_record, "_engine") and connection_record._engine is not None:
        url_str = str(connection_record._engine.url)
    
    # Check both engine URL or dbapi connection type
    if "sqlite" in url_str or dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def ensure_sqlite_directory(database_url: str) -> None:
    """Ensure the target directory exists if connecting to a file-based SQLite database."""
    if database_url.startswith("sqlite:///") and ":memory:" not in database_url:
        db_path = database_url.replace("sqlite:///", "", 1)
        dir_name = os.path.dirname(db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)


def get_engine(database_url: Optional[str] = None, **kwargs) -> Engine:
    """Create and return a configured SQLAlchemy engine."""
    url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    
    connect_args = kwargs.pop("connect_args", {})
    if "sqlite" in url:
        ensure_sqlite_directory(url)
        connect_args.setdefault("check_same_thread", False)
        
    return create_engine(url, connect_args=connect_args, **kwargs)


def get_session_factory(bind_engine: Optional[Engine] = None) -> sessionmaker[Session]:
    """Create and return a sessionmaker bound to the given or default engine."""
    target_engine = bind_engine or engine
    return sessionmaker(autocommit=False, autoflush=False, bind=target_engine)


# Global default engine and session factory
engine: Engine = get_engine()
SessionLocal: sessionmaker[Session] = get_session_factory(engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI context-managed dependency that yields thread-safe database sessions."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context(target_engine: Optional[Engine] = None) -> Generator[Session, None, None]:
    """Context manager for standalone scripts or tasks outside request scopes."""
    factory = get_session_factory(target_engine) if target_engine else SessionLocal
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine: Optional[Engine] = None) -> None:
    """Create all relational tables defined in the Base metadata."""
    target = target_engine or engine
    Base.metadata.create_all(bind=target)


def reset_db(target_engine: Optional[Engine] = None) -> None:
    """Drop and recreate all relational tables."""
    target = target_engine or engine
    Base.metadata.drop_all(bind=target)
    Base.metadata.create_all(bind=target)
