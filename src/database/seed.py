"""Database seeding CLI script for Dominican Republic food businesses and initial users."""

import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.database.security import hash_password
from src.database.session import (
    engine,
    get_session_factory,
    init_db,
    reset_db,
)
from src.models.entities import Business, Container, User
from src.models.enums import BusinessType, ContainerStatus, UserRole

DEFAULT_SEED_FILE = os.path.join(
    os.path.dirname(__file__), "seed_data", "dominican_businesses.json"
)

# Admin users as required by the specification
SYSTEM_ADMINS = [
    {"email": "czorrilla@sicra.do", "full_name": "Carlos Zorrilla"},
    {"email": "dcaraballo@sicra.do", "full_name": "Daniel Caraballo"},
    {"email": "yrodriguez@sicra.do", "full_name": "Yomaira Rodriguez"},
    {"email": "fcharles@sicra.do", "full_name": "Frank Charles"},
    {"email": "amontero@sicra.do", "full_name": "Alexander Montero"},
    {"email": "jburgos@sicra.do", "full_name": "Jose Burgos"},
    {"email": "mcarrasco@sicra.do", "full_name": "Manuel Carrasco"},
    {"email": "admin@sicra.do", "full_name": "Administrador General"},
]

COLLECTOR_USERS = [
    {"email": "operaciones@reoil.do", "full_name": "Operaciones Reoil"},
    {"email": "logistica@mevosa.do", "full_name": "Logística Mevosa"},
]

ADMIN_PASSWORD = "AdminSecure2026!"
COLLECTOR_PASSWORD = "CollectorSecure2026!"
OWNER_PASSWORD = "OwnerSecure2026!"


def load_seed_data(file_path: str = DEFAULT_SEED_FILE) -> List[Dict[str, Any]]:
    """Load business seed specifications from JSON."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_device_token(key: str) -> str:
    """Generate a stable, secure device token based on business key."""
    hex16 = hashlib.sha256(f"sicra_token_salt_{key}".encode("utf-8")).hexdigest()[:16]
    return f"sicra_live_tok_{key.lower()}_{hex16}"


def seed_database(
    target_engine: Optional[Engine] = None,
    reset: bool = False,
    quiet: bool = False,
    seed_file: str = DEFAULT_SEED_FILE,
) -> Dict[str, int]:
    """Populate the database with pilot businesses, containers, and RBAC users."""
    eng = target_engine or engine

    if reset:
        if not quiet:
            print("Resetting database tables...")
        reset_db(eng)
    else:
        init_db(eng)

    session_factory = get_session_factory(eng)
    session: Session = session_factory()

    stats = {
        "businesses_created": 0,
        "businesses_skipped": 0,
        "containers_created": 0,
        "containers_skipped": 0,
        "users_created": 0,
        "users_skipped": 0,
    }

    try:
        # 1. Seed System Administrators
        admin_hash = hash_password(ADMIN_PASSWORD)
        for admin in SYSTEM_ADMINS:
            existing = session.query(User).filter(User.email == admin["email"]).first()
            if existing:
                stats["users_skipped"] += 1
            else:
                user = User(
                    email=admin["email"],
                    hashed_password=admin_hash,
                    full_name=admin["full_name"],
                    role=UserRole.ADMIN,
                    business_id=None,
                    is_active=True,
                )
                session.add(user)
                stats["users_created"] += 1

        # 2. Seed Authorized Collectors
        collector_hash = hash_password(COLLECTOR_PASSWORD)
        for collector in COLLECTOR_USERS:
            existing = session.query(User).filter(User.email == collector["email"]).first()
            if existing:
                stats["users_skipped"] += 1
            else:
                user = User(
                    email=collector["email"],
                    hashed_password=collector_hash,
                    full_name=collector["full_name"],
                    role=UserRole.COLLECTOR,
                    business_id=None,
                    is_active=True,
                )
                session.add(user)
                stats["users_created"] += 1

        session.commit()

        # 3. Seed Businesses, Containers, and Business Owners
        biz_seeds = load_seed_data(seed_file)
        owner_hash = hash_password(OWNER_PASSWORD)

        for item in biz_seeds:
            # Check for existing business by unique name or address
            biz = session.query(Business).filter(Business.name == item["name"]).first()
            if biz:
                stats["businesses_skipped"] += 1
            else:
                biz = Business(
                    name=item["name"],
                    business_type=BusinessType(item["business_type"]),
                    num_fryers=item["num_fryers"],
                    avg_daily_customers=item["avg_daily_customers"],
                    latitude=item["latitude"],
                    longitude=item["longitude"],
                    address=item["address"],
                    city=item["city"],
                    contact_name=item.get("contact_name"),
                    phone=item.get("phone"),
                    is_active=True,
                )
                session.add(biz)
                session.flush()  # populate biz.id
                stats["businesses_created"] += 1

            # Check or create Container
            token = generate_device_token(item["key"])
            container = (
                session.query(Container)
                .filter(Container.device_token == token)
                .first()
            )
            if not container:
                # Also check by business_id
                container = (
                    session.query(Container)
                    .filter(Container.business_id == biz.id)
                    .first()
                )

            if container:
                stats["containers_skipped"] += 1
            else:
                # Determine capacity tier and tare weight if not explicitly provided
                fryers = item["num_fryers"]
                if fryers >= 4:
                    cap = 100.0
                    tare = 6.50
                elif fryers >= 2:
                    cap = 50.0
                    tare = 3.80
                else:
                    cap = 20.0
                    tare = 2.20

                capacity = item.get("capacity_liters", cap)
                tare_weight = item.get("tare_weight_kg", tare)

                container = Container(
                    business_id=biz.id,
                    device_token=token,
                    capacity_liters=capacity,
                    tare_weight_kg=tare_weight,
                    oil_density_kg_l=0.92,
                    status=ContainerStatus.ACTIVE,
                    current_volume_liters=0.0,
                    current_fill_percentage=0.0,
                )
                session.add(container)
                stats["containers_created"] += 1

            # Check or create Business Owner User
            owner_email = item.get("owner_email")
            if owner_email:
                owner_user = (
                    session.query(User).filter(User.email == owner_email).first()
                )
                if owner_user:
                    stats["users_skipped"] += 1
                else:
                    owner_user = User(
                        email=owner_email,
                        hashed_password=owner_hash,
                        full_name=item.get("owner_name", item["name"]),
                        role=UserRole.BUSINESS_OWNER,
                        business_id=biz.id,
                        is_active=True,
                    )
                    session.add(owner_user)
                    stats["users_created"] += 1

        session.commit()

        if not quiet:
            print("\nSeeding complete!")
            print(f"  Businesses: {stats['businesses_created']} created, {stats['businesses_skipped']} skipped")
            print(f"  Containers: {stats['containers_created']} created, {stats['containers_skipped']} skipped")
            print(f"  Users:      {stats['users_created']} created, {stats['users_skipped']} skipped\n")

        return stats

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    """CLI entrypoint for seeding command."""
    parser = argparse.ArgumentParser(description="SICRA Dominican Republic Seeding CLI")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all existing tables before seeding",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output messages",
    )
    parser.add_argument(
        "--seed-file",
        type=str,
        default=DEFAULT_SEED_FILE,
        help="Custom path to businesses seed JSON file",
    )
    args = parser.parse_args()

    seed_database(reset=args.reset, quiet=args.quiet, seed_file=args.seed_file)


if __name__ == "__main__":
    main()
