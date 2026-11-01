"""Database configuration, engine factory, migration, security, and session helpers."""

from typing import TYPE_CHECKING
from src.database.session import (
    DEFAULT_DATABASE_URL,
    SessionLocal,
    engine,
    get_db,
    get_db_context,
    get_engine,
    get_session_factory,
    init_db,
    reset_db,
)

if TYPE_CHECKING:
    from src.database.init_db import initialize_database
    from src.database.security import hash_password, verify_password
    from src.database.seed import seed_database

__all__ = [
    "DEFAULT_DATABASE_URL",
    "engine",
    "SessionLocal",
    "get_engine",
    "get_session_factory",
    "get_db",
    "get_db_context",
    "init_db",
    "reset_db",
    "initialize_database",
    "hash_password",
    "verify_password",
    "seed_database",
]


def __getattr__(name: str):
    if name == "initialize_database":
        from src.database.init_db import initialize_database
        return initialize_database
    if name in ("hash_password", "verify_password"):
        from src.database import security
        return getattr(security, name)
    if name == "seed_database":
        from src.database.seed import seed_database
        return seed_database
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
