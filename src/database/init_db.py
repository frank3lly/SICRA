"""Programmatic database table initialization helper for lightweight execution."""

import argparse
import sys
from typing import Optional
from sqlalchemy.engine import Engine

from src.database.session import engine, init_db, reset_db


def initialize_database(target_engine: Optional[Engine] = None, reset: bool = False) -> None:
    """Create or reset database tables programmatically without executing raw migration scripts."""
    eng = target_engine or engine
    if reset:
        reset_db(eng)
        print("Database tables dropped and recreated successfully.")
    else:
        init_db(eng)
        print("Database tables initialized successfully.")


def main() -> None:
    """CLI entrypoint for database initialization."""
    parser = argparse.ArgumentParser(description="SICRA Programmatic Database Initializer")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all existing tables before initialization",
    )
    args = parser.parse_args()
    initialize_database(reset=args.reset)


if __name__ == "__main__":
    main()
