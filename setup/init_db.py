"""
Initialize the NFL database schema.

Connects to PostgreSQL using credentials from .env and executes all SQL
schema files to create tables. Safe to re-run — uses CREATE TABLE IF NOT EXISTS.

Usage:
    python -m setup.init_db
"""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


SCHEMA_DIR = Path("setup/schema")

# Order matters if we add foreign keys later
SCHEMA_FILES = [
    "players.sql",
    "schedules.sql",
    "player_stats.sql",
]


def get_connection() -> psycopg2.extensions.connection:
    """
    Create a PostgreSQL connection using credentials from .env.

    Returns:
        Active psycopg2 connection.
    """
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def init_db() -> None:
    """Execute all schema SQL files to create tables."""
    conn = get_connection()
    cur = conn.cursor()

    for filename in SCHEMA_FILES:
        filepath = SCHEMA_DIR / filename
        if not filepath.exists():
            print(f"WARNING: {filepath} not found, skipping.")
            continue

        sql = filepath.read_text(encoding="utf-8")
        cur.execute(sql)
        print(f"Executed {filepath}")

    conn.commit()
    cur.close()
    conn.close()
    print("\nSchema initialization complete.")


if __name__ == "__main__":
    init_db()