# NFL Data Project

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue)
![Docker](https://img.shields.io/badge/Docker-ready-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A production-grade NFL statistics database built from [nflverse](https://nflverse.nflverse.com/) open-source data. The project pulls cleaned NFL data via the `nflreadpy` Python library, transforms it with Pandas, and loads it into a normalized PostgreSQL schema using idempotent batch upserts. The current dataset covers **24,376 players, 7,276 games, and 475,626 weekly player stat lines** spanning 1999 to the present.


## What's in the box

The repo contains an end-to-end pipeline from raw upstream data to a queryable relational database:

- **Three loader scripts** (`loaders/`) that fetch data from nflverse, transform it, and upsert into Postgres
- **SQL schema files** (`setup/schema/`) defining three tables with documented column choices
- **A database initializer** (`setup/init_db.py`) that creates the schema on a fresh DB
- **Docker-based Postgres** for a reproducible environment, no local install required

## Tech Stack

| Component | Choice | Why |
| --- | --- | --- |
| Database | PostgreSQL 17 (Docker) | Mature, free, excellent for analytical queries |
| Language | Python 3.12 | Standard for data work; great library ecosystem |
| Data source | nflverse via `nflreadpy` | CC-BY 4.0 licensed, nightly updates, well-maintained |
| DataFrames | Pandas | Mature ecosystem; converts cleanly from Polars output |
| DB driver | `psycopg2-binary` | Reliable, supports `execute_values` for fast batch inserts |
| Containerization | Docker Compose | One-command local DB; reproducible across machines |

## Schema Overview

Three tables, all with `created_at` / `updated_at` timestamps and idempotent upsert support:

### `players` — 28 data columns, 24,376 rows
Master player lookup table. Primary key is `gsis_id` (the NFL's GSIS identifier, e.g. `00-0033873`). Contains biographical info, draft data, and cross-platform IDs (ESPN, PFR, PFF, OTC) for future joins to external data sources.

### `schedules` — 44 data columns, 7,276 rows (1999–2025)
Game-level data. Primary key is `game_id` in the format `{season}_{week}_{away}_{home}` (e.g. `2024_01_BAL_KC`). Includes scores, betting lines, weather, starting QBs, coaches, referee, and stadium.

### `player_stats` — 113 data columns, 475,626 rows
Per-player, per-week statistics. Composite primary key on `(player_id, season, week)`. The `player_id` here is a GSIS ID matching `players.gsis_id`, enabling clean joins. 


## Design Decisions

A handful of small choices that shaped the project. I called these out because they're the kind of small reasoned trade-offs that compound across a real codebase.

- **Idempotent upserts via `INSERT ... ON CONFLICT`.** Every loader is safe to re-run. Re-running refreshes data (scores after games complete, betting lines as they move) instead of erroring or duplicating.
- **`execute_values` with `page_size=1000` for batch inserts.** Row-by-row inserts on 475K rows are pathologically slow. Batch inserts run the same load in seconds.
- **No foreign key from `player_stats.player_id` to `players.gsis_id` (yet).** This avoids load-order dependency between loaders and tolerates edge cases where stats reference a player ID not in the players table. Foreign keys can be added later once query patterns stabilize.
- **`REAL` instead of `DOUBLE PRECISION` for floats.** Stats and betting lines don't need 64-bit precision. `REAL` is half the storage and identical in practice for this domain.


## Setup

### Prerequisites
- Docker Desktop (or any Docker engine)
- Python 3.12
- Git

### Steps

```bash
# 1. Clone
git clone https://github.com/nicky-eyes/nfl_data.git
cd nfl_data

# 2. Create .env from template (then edit with your credentials)
cp .env.example .env

# 3. Start Postgres
docker-compose up -d

# 4. Set up Python environment
python -m venv .venv
.venv\Scripts\activate                  # Windows
# source .venv/bin/activate              # macOS / Linux
pip install -r requirements.txt

# 5. Initialize the database schema
python -m setup.init_db

# 6. Load the data (each loader is independent)
python -m loaders.load_players
python -m loaders.load_schedules
python -m loaders.load_player_stats
```

The full backfill loads roughly 500K rows across the three tables. Player stats is the largest and takes the longest — typically 1-3 minutes depending on network and machine.


## Data Source & Attribution

All NFL data in this project comes from [nflverse](https://nflverse.nflverse.com/), a community-maintained open data project. The data is licensed under [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) and is accessed via [`nflreadpy`](https://github.com/nflverse/nflreadpy).

If you build on this project or use the data downstream, please attribute nflverse appropriately.


## License

MIT — see `LICENSE` for details.
