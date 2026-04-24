"""
Load NFL player stats from nflreadpy into the player_stats table.

Fetches per-player, per-week statistics across all seasons by default
(1999-present), filters out null-player_id placeholder rows, and upserts
in batch. Idempotent — re-running updates stats (useful mid-season as
nflverse refreshes data nightly).

Usage:
    python -m loaders.load_player_stats
"""

import os
from typing import Iterable, Union

import nflreadpy as nfl
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


# Column order for INSERT — must match player_stats.sql exactly.
# Includes game_id (added to nflverse schema after initial design).
INSERT_COLUMNS = [
    "player_id",
    "player_name",
    "player_display_name",
    "position",
    "position_group",
    "headshot_url",
    "season",
    "week",
    "season_type",
    "game_id",
    "team",
    "opponent_team",
    # Passing
    "completions",
    "attempts",
    "passing_yards",
    "passing_tds",
    "passing_interceptions",
    "sacks_suffered",
    "sack_yards_lost",
    "sack_fumbles",
    "sack_fumbles_lost",
    "passing_air_yards",
    "passing_yards_after_catch",
    "passing_first_downs",
    "passing_epa",
    "passing_cpoe",
    "passing_2pt_conversions",
    "pacr",
    # Rushing
    "carries",
    "rushing_yards",
    "rushing_tds",
    "rushing_fumbles",
    "rushing_fumbles_lost",
    "rushing_first_downs",
    "rushing_epa",
    "rushing_2pt_conversions",
    # Receiving
    "receptions",
    "targets",
    "receiving_yards",
    "receiving_tds",
    "receiving_fumbles",
    "receiving_fumbles_lost",
    "receiving_air_yards",
    "receiving_yards_after_catch",
    "receiving_first_downs",
    "receiving_epa",
    "receiving_2pt_conversions",
    "racr",
    "target_share",
    "air_yards_share",
    "wopr",
    # Special teams
    "special_teams_tds",
    # Defense
    "def_tackles_solo",
    "def_tackles_with_assist",
    "def_tackle_assists",
    "def_tackles_for_loss",
    "def_tackles_for_loss_yards",
    "def_fumbles_forced",
    "def_sacks",
    "def_sack_yards",
    "def_qb_hits",
    "def_interceptions",
    "def_interception_yards",
    "def_pass_defended",
    "def_tds",
    "def_fumbles",
    "def_safeties",
    # Miscellaneous
    "misc_yards",
    "fumble_recovery_own",
    "fumble_recovery_yards_own",
    "fumble_recovery_opp",
    "fumble_recovery_yards_opp",
    "fumble_recovery_tds",
    "penalties",
    "penalty_yards",
    # Returns
    "punt_returns",
    "punt_return_yards",
    "kickoff_returns",
    "kickoff_return_yards",
    # Kicking
    "fg_made",
    "fg_att",
    "fg_missed",
    "fg_blocked",
    "fg_long",
    "fg_pct",
    "fg_made_0_19",
    "fg_made_20_29",
    "fg_made_30_39",
    "fg_made_40_49",
    "fg_made_50_59",
    "fg_made_60_",
    "fg_missed_0_19",
    "fg_missed_20_29",
    "fg_missed_30_39",
    "fg_missed_40_49",
    "fg_missed_50_59",
    "fg_missed_60_",
    "fg_made_list",
    "fg_missed_list",
    "fg_blocked_list",
    "fg_made_distance",
    "fg_missed_distance",
    "fg_blocked_distance",
    "pat_made",
    "pat_att",
    "pat_missed",
    "pat_blocked",
    "pat_pct",
    "gwfg_made",
    "gwfg_att",
    "gwfg_missed",
    "gwfg_blocked",
    "gwfg_distance",
    # Fantasy
    "fantasy_points",
    "fantasy_points_ppr",
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


def fetch_player_stats(
    seasons: Union[bool, Iterable[int]] = True,
) -> pd.DataFrame:
    """
    Fetch player stats from nflreadpy.

    Args:
        seasons: Which seasons to fetch. True pulls all history (1999-present),
            False pulls current season only, or pass an iterable of years
            (e.g. [2023, 2024]) for specific seasons.

    Returns:
        DataFrame with all nflreadpy player_stats columns.
    """
    print(f"Fetching player stats from nflreadpy (seasons={seasons})...")
    df = nfl.load_player_stats(seasons=seasons).to_pandas()
    print(f"  Retrieved {len(df):,} rows with {len(df.columns)} columns")
    return df


def transform_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter out placeholder rows, normalize NaN to None, reorder columns.

    Placeholder rows have a null player_id and are all-zero stats that
    nflverse inserts as structural padding — they're not real observations
    and should not be loaded.

    Args:
        df: Raw player_stats DataFrame from nflreadpy.

    Returns:
        DataFrame with only schema columns, in INSERT_COLUMNS order, with
        null-player_id rows removed.
    """
    before = len(df)
    df = df[df["player_id"].notna()].copy()
    removed = before - len(df)
    print(f"  Filtered {removed} placeholder rows (null player_id)")

    # Replace pandas NaN with None so psycopg2 writes SQL NULL.
    df = df.astype(object).where(pd.notnull(df), None)
    df = df[INSERT_COLUMNS]
    return df


def upsert_player_stats(
    conn: psycopg2.extensions.connection, df: pd.DataFrame
) -> int:
    """
    Upsert player stats into the player_stats table in batched statements.

    The primary key is composite (player_id, season, week). On conflict,
    all non-key columns are overwritten and updated_at is refreshed.

    Args:
        conn: Active psycopg2 connection.
        df: Transformed DataFrame with columns matching INSERT_COLUMNS.

    Returns:
        Number of rows processed.
    """
    pk_cols = {"player_id", "season", "week"}
    update_cols = [c for c in INSERT_COLUMNS if c not in pk_cols]
    update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    sql = f"""
        INSERT INTO player_stats ({", ".join(INSERT_COLUMNS)})
        VALUES %s
        ON CONFLICT (player_id, season, week) DO UPDATE SET
            {update_clause},
            updated_at = CURRENT_TIMESTAMP;
    """

    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    conn.commit()
    return len(rows)


def load_player_stats(seasons: Union[bool, Iterable[int]] = True) -> None:
    """
    Run the full ETL: fetch, filter, transform, upsert.

    Args:
        seasons: Passed through to fetch_player_stats. Defaults to True
            (all seasons, for initial backfill).
    """
    df = fetch_player_stats(seasons=seasons)
    df = transform_player_stats(df)
    print(f"Transformed to {len(df):,} rows x {len(df.columns)} columns")

    conn = get_connection()
    try:
        count = upsert_player_stats(conn, df)
        print(f"Upserted {count:,} rows into the player_stats table.")
    finally:
        conn.close()


if __name__ == "__main__":
    load_player_stats()