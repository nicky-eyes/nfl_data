"""
Load NFL schedules from nflreadpy into the schedules table.

Fetches the full schedules dataset (all seasons from 1999), drops columns not
in our schema, converts pandas NaN to None for PostgreSQL, and upserts in batch.
Idempotent — re-running updates scores and betting lines as games complete.

Usage:
    python -m loaders.load_schedules
"""

import os

import nflreadpy as nfl
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


# Columns from nflreadpy that we do NOT persist — see setup/schema/schedules.sql.
DROP_COLUMNS = [
    "nfl_detail_id",
    "pff",
]

# Column order for INSERT — must match schedules.sql and the VALUES tuples.
INSERT_COLUMNS = [
    "game_id",
    "season",
    "game_type",
    "week",
    "gameday",
    "weekday",
    "gametime",
    "away_team",
    "away_score",
    "home_team",
    "home_score",
    "location",
    "result",
    "total",
    "overtime",
    "old_game_id",
    "gsis",
    "pfr",
    "espn",
    "ftn",
    "away_rest",
    "home_rest",
    "away_moneyline",
    "home_moneyline",
    "spread_line",
    "away_spread_odds",
    "home_spread_odds",
    "total_line",
    "under_odds",
    "over_odds",
    "div_game",
    "roof",
    "surface",
    "temp",
    "wind",
    "away_qb_id",
    "home_qb_id",
    "away_qb_name",
    "home_qb_name",
    "away_coach",
    "home_coach",
    "referee",
    "stadium_id",
    "stadium",
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


def fetch_schedules() -> pd.DataFrame:
    """
    Fetch all schedules from nflreadpy and return as a pandas DataFrame.

    Returns:
        DataFrame with all nflreadpy schedules columns across all seasons.
    """
    print("Fetching schedules from nflreadpy...")
    df = nfl.load_schedules().to_pandas()
    print(f"  Retrieved {len(df):,} games with {len(df.columns)} columns")
    return df


def transform_schedules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop unused columns, normalize NaN to None, reorder to INSERT order.

    Args:
        df: Raw schedules DataFrame from nflreadpy.

    Returns:
        DataFrame with only schema columns, in INSERT_COLUMNS order.
    """
    df = df.drop(columns=DROP_COLUMNS)
    # Replace pandas NaN with None so psycopg2 writes SQL NULL.
    df = df.astype(object).where(pd.notnull(df), None)
    df = df[INSERT_COLUMNS]
    return df


def upsert_schedules(conn: psycopg2.extensions.connection, df: pd.DataFrame) -> int:
    """
    Upsert schedules into the schedules table in a single batch statement.

    On conflict (same game_id), all non-key columns are overwritten and
    updated_at is refreshed. This allows re-running the loader mid-season
    to pick up final scores and updated betting lines.

    Args:
        conn: Active psycopg2 connection.
        df: Transformed DataFrame with columns matching INSERT_COLUMNS.

    Returns:
        Number of rows processed.
    """
    update_cols = [c for c in INSERT_COLUMNS if c != "game_id"]
    update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    sql = f"""
        INSERT INTO schedules ({", ".join(INSERT_COLUMNS)})
        VALUES %s
        ON CONFLICT (game_id) DO UPDATE SET
            {update_clause},
            updated_at = CURRENT_TIMESTAMP;
    """

    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    conn.commit()
    return len(rows)


def load_schedules() -> None:
    """Run the full ETL: fetch, transform, upsert."""
    df = fetch_schedules()
    df = transform_schedules(df)
    print(f"Transformed to {len(df.columns)} schema columns")

    conn = get_connection()
    try:
        count = upsert_schedules(conn, df)
        print(f"Upserted {count:,} games into the schedules table.")
    finally:
        conn.close()


if __name__ == "__main__":
    load_schedules()