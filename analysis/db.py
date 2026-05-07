"""
Shared utilities for analysis notebooks.

Centralizes the database connection, the query helper, and global plot
styling so individual notebooks can stay focused on the analysis itself.

Usage from a notebook in analysis/:
    from db import run_query, apply_plot_style
    apply_plot_style()
    df = run_query("SELECT * FROM schedules LIMIT 5")
"""

import os
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


# resolve .env relative to this file, not the notebook's working directory.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


def get_engine() -> Engine:
    """Build a SQLAlchemy engine for the project's PostgreSQL database."""
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


# A single engine for the lifetime of the notebook session.
_ENGINE: Engine = get_engine()


def run_query(sql: str) -> pd.DataFrame:
    """Execute a SQL query and return the result as a pandas DataFrame."""
    with _ENGINE.connect() as conn:
        return pd.read_sql(sql, conn)


def apply_plot_style() -> None:
    """Apply consistent matplotlib/seaborn styling across all notebooks."""
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams["figure.figsize"] = (11, 5)
    plt.rcParams["axes.titlesize"] = 14
    plt.rcParams["axes.titleweight"] = "bold"