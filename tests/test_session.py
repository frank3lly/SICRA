"""Unit tests for database engine factory and session management."""

from unittest.mock import MagicMock
import os
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.session import (
    get_db,
    get_db_context,
    get_engine,
    get_session_factory,
    init_db,
    reset_db,
)
from src.models import Business, BusinessType


def test_sqlite_pragma_enforcement():
    """Verify foreign_keys pragma is enabled on SQLite connections."""
    test_engine = get_engine("sqlite:///:memory:")
    with test_engine.connect() as conn:
        res = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert res == 1


def test_get_engine_creates_directory(tmp_path):
    """Verify SQLite directory creation for nested paths."""
    db_file = tmp_path / "subdir" / "test_sicra.db"
    url = f"sqlite:///{db_file}"
    engine = get_engine(url)
    init_db(engine)
    assert os.path.exists(db_file)


def test_get_db_dependency():
    """Verify get_db generator yields and properly closes session."""
    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)
    session.close = MagicMock()
    try:
        next(gen)
    except StopIteration:
        pass
    session.close.assert_called_once()


def test_get_db_context_manager():
    """Verify get_db_context manager works with in-memory test engine."""
    test_engine = get_engine("sqlite:///:memory:")
    init_db(test_engine)

    with get_db_context(test_engine) as session:
        biz = Business(
            name="Cafeteria Mirador",
            business_type=BusinessType.CAFETERIA,
            latitude=18.45,
            longitude=-69.30,
            address="Av. Malecon",
        )
        session.add(biz)
        session.commit()
        biz_id = biz.id

    with get_db_context(test_engine) as session:
        queried = session.get(Business, biz_id)
        assert queried is not None
        assert queried.name == "Cafeteria Mirador"


def test_reset_db():
    """Verify reset_db drops and recreates tables."""
    test_engine = get_engine("sqlite:///:memory:")
    init_db(test_engine)
    with get_db_context(test_engine) as session:
        session.add(
            Business(
                name="Test Biz",
                business_type=BusinessType.FRITURA,
                latitude=18.4,
                longitude=-69.3,
                address="Test",
            )
        )
        session.commit()

    reset_db(test_engine)
    with get_db_context(test_engine) as session:
        assert len(session.query(Business).all()) == 0
