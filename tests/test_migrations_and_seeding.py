"""Unit and integration tests for database migrations, initialization, and seeding."""

import os
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from src.database.init_db import initialize_database
from src.database.security import hash_password, verify_password
from src.database.seed import seed_database
from src.database.session import get_engine, get_session_factory
from src.models import Business, Container, ContainerStatus, User, UserRole


@pytest.fixture
def test_engine(tmp_path):
    """File-backed SQLite engine in a temporary directory."""
    db_path = tmp_path / "test_migration_seed.db"
    url = f"sqlite:///{db_path}"
    return get_engine(url)


def test_alembic_migrations(tmp_path):
    """Verify Alembic migration pipeline can upgrade to head and downgrade to base."""
    db_path = tmp_path / "alembic_test.db"
    url = f"sqlite:///{db_path}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", url)

    # 1. Upgrade to latest migration (0001)
    command.upgrade(alembic_cfg, "head")

    eng = get_engine(url)
    inspector = inspect(eng)
    tables = set(inspector.get_table_names())
    expected = {
        "businesses",
        "containers",
        "telemetries",
        "predictions",
        "alerts",
        "collection_routes",
        "users",
        "alembic_version",
    }
    assert expected.issubset(tables)

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(eng)
    downgraded_tables = set(inspector.get_table_names())
    assert "businesses" not in downgraded_tables
    assert "containers" not in downgraded_tables


def test_init_db_helper(test_engine):
    """Verify programmatic database initialization without migrations."""
    initialize_database(target_engine=test_engine, reset=True)
    inspector = inspect(test_engine)
    tables = set(inspector.get_table_names())
    expected = {
        "businesses",
        "containers",
        "telemetries",
        "predictions",
        "alerts",
        "collection_routes",
        "users",
    }
    assert expected.issubset(tables)


def test_seed_database_verification(test_engine):
    """Verify seed execution and acceptance criteria."""
    stats = seed_database(target_engine=test_engine, reset=True, quiet=True)

    # Assert exactly 11 businesses created
    assert stats["businesses_created"] == 11
    assert stats["containers_created"] == 11
    assert stats["users_created"] == 21

    session_factory = get_session_factory(test_engine)
    with session_factory() as session:
        businesses = session.query(Business).all()
        assert len(businesses) == 11

        for biz in businesses:
            # 1. Check coordinates within San Pedro de Macorís bounding box
            assert 18.40 <= biz.latitude <= 18.50, f"Latitude {biz.latitude} out of SPM bounds for {biz.name}"
            assert -69.35 <= biz.longitude <= -69.25, f"Longitude {biz.longitude} out of SPM bounds for {biz.name}"

            # 2. Check linked container
            assert len(biz.containers) == 1, f"Business {biz.name} does not have exactly one container"
            container = biz.containers[0]
            assert container.status == ContainerStatus.ACTIVE
            assert container.oil_density_kg_l == 0.92
            assert container.device_token.startswith("sicra_live_tok_")

            # 3. Check capacity tiers
            if biz.num_fryers >= 4:
                assert container.capacity_liters == 100.0, f"Expected 100L for {biz.name}"
                assert container.tare_weight_kg == 6.50
            elif biz.num_fryers >= 2:
                assert container.capacity_liters == 50.0, f"Expected 50L for {biz.name}"
                assert container.tare_weight_kg == 3.80
            else:
                assert container.capacity_liters == 20.0, f"Expected 20L for {biz.name}"
                assert container.tare_weight_kg == 2.20

            # 4. Check linked business owner user
            owner_users = session.query(User).filter(User.business_id == biz.id).all()
            assert len(owner_users) == 1
            owner = owner_users[0]
            assert owner.role == UserRole.BUSINESS_OWNER
            assert verify_password("OwnerSecure2026!", owner.hashed_password)

        # 5. Check System Admins
        admins = session.query(User).filter(User.role == UserRole.ADMIN).all()
        assert len(admins) == 8
        admin_emails = {a.email for a in admins}
        expected_admin_emails = {
            "czorrilla@sicra.do",
            "dcaraballo@sicra.do",
            "yrodriguez@sicra.do",
            "fcharles@sicra.do",
            "amontero@sicra.do",
            "jburgos@sicra.do",
            "mcarrasco@sicra.do",
            "admin@sicra.do",
        }
        assert expected_admin_emails == admin_emails
        for admin in admins:
            assert verify_password("AdminSecure2026!", admin.hashed_password)
            assert not verify_password("WrongPassword123!", admin.hashed_password)

        # 6. Check Authorized Collectors
        collectors = session.query(User).filter(User.role == UserRole.COLLECTOR).all()
        assert len(collectors) == 2
        collector_emails = {c.email for c in collectors}
        assert collector_emails == {"operaciones@reoil.do", "logistica@mevosa.do"}
        for col in collectors:
            assert verify_password("CollectorSecure2026!", col.hashed_password)


def test_seed_database_idempotency(test_engine):
    """Verify running seed multiple times without --reset skips duplicates gracefully."""
    # First seed
    seed_database(target_engine=test_engine, reset=True, quiet=True)

    # Second seed (idempotency check)
    stats2 = seed_database(target_engine=test_engine, reset=False, quiet=True)
    assert stats2["businesses_created"] == 0
    assert stats2["businesses_skipped"] == 11
    assert stats2["containers_created"] == 0
    assert stats2["containers_skipped"] == 11
    assert stats2["users_created"] == 0
    assert stats2["users_skipped"] == 21
