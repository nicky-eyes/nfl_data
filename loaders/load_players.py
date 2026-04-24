"""
Load NFL players from nflreadpy into the players table.

Fetches the full players dataset, drops columns not in our schema, converts
pandas NaN to None for PostgreSQL, and upserts in batch using execute_values.
Idempotent — safe to re-run. ON CONFLICT updates existing rows and refreshes
the updated_at timestamp.

Usage:
    python -m loaders.load_players
"""

import os
from pathlib import Path

import nflreadpy as nfl
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


# Columns from nflreadpy that we drop — see setup/schema/players.sql
DROP_COLUMNS = [
    "common_first_name",
    "short_name",
    "football_name",
    "suffix",
    "ngs_position_group",
    "ngs_position",
    "headshot",
    "ngs_status",
    "ngs_status_short_description",
    "pff_position",
    "pff_status",
]

# Column order for insert 
INSERT_COLUMNS = [
    "gsis_id",
    "display_name",
    "first_name",
    "last_name",
    "position",
    "position_group",
    "jersey_number",
    "height",
    "weight",
    "birth_date",
    "college_name",
    "college_conference",
    "rookie_season",
    "last_season",
    "latest_team",
    "status",
    "years_of_experience",
    "draft_year",
    "draft_round",
    "draft_pick",
    "draft_team",
    "esb_id",
    "nfl_id",
    "pfr_id",
    "pff_id",
    "otc_id",
    "espn_id",
    "smart_id",
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


def fetch_players() -> pd.DataFrame:
    """
    Fetch all players from nflreadpy and return as a pandas DataFrame.

    Returns:
        DataFrame with all nflreadpy player columns.
    """
    print("Fetching players from nflreadpy...")
    df = nfl.load_players().to_pandas()
    print(f"  Retrieved {len(df):,} players with {len(df.columns)} columns")
    return df


def transform_players(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop unused columns and reorder to match INSERT_COLUMNS.

    Args:
        df: Raw players DataFrame from nflreadpy.

    Returns:
        DataFrame with only schema columns, in INSERT order.
    """
    df = df.drop(columns=DROP_COLUMNS)
    # Replace pandas NaN with None so psycopg2 writes SQL NULL.
    df = df.astype(object).where(pd.notnull(df), None)
    # Reorder to match INSERT_COLUMNS exactly.
    df = df[INSERT_COLUMNS]
    return df


def upsert_players(conn: psycopg2.extensions.connection, df: pd.DataFrame) -> int:
    """
    Upsert players into the players table in a single batch statement.

    On conflict (same gsis_id), all non-key columns are overwritten and
    updated_at is refreshed.

    Args:
        conn: Active psycopg2 connection.
        df: Transformed DataFrame with columns matching INSERT_COLUMNS.

    Returns:
        Number of rows processed.
    """
    # Build the "col = EXCLUDED.col" list for every column except the PK.
    update_cols = [c for c in INSERT_COLUMNS if c != "gsis_id"]
    update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    sql = f"""
        INSERT INTO players ({", ".join(INSERT_COLUMNS)})
        VALUES %s
        ON CONFLICT (gsis_id) DO UPDATE SET
            {update_clause},
            updated_at = CURRENT_TIMESTAMP;
    """

    # DataFrame rows -> list of tuples for execute_values.
    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    conn.commit()
    return len(rows)


def load_players() -> None:
    """Run the full ETL: fetch, transform, upsert."""
    df = fetch_players()
    df = transform_players(df)
    print(f"Transformed to {len(df.columns)} schema columns")

    conn = get_connection()
    try:
        count = upsert_players(conn, df)
        print(f"Upserted {count:,} players into the players table.")
    finally:
        conn.close()


if __name__ == "__main__":
    load_players()