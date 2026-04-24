-- Schedules: game-level data including scores, betting lines, weather, and metadata.
-- Primary key is game_id in the format {season}_{week}_{away}_{home} (e.g. 2024_01_BAL_KC).
--
-- Columns dropped from nflreadpy output:
--   nfl_detail_id — NFL internal game ID (100% null in 2024)
--   pff           — Pro Football Focus game ID (100% null in 2024)

CREATE TABLE IF NOT EXISTS schedules (
    game_id             VARCHAR(30) PRIMARY KEY,
    season              INT NOT NULL,
    game_type           VARCHAR(10) NOT NULL,
    week                INT NOT NULL,
    gameday             VARCHAR(15) NOT NULL,
    weekday             VARCHAR(15) NOT NULL,
    gametime            VARCHAR(10),
    away_team           VARCHAR(5) NOT NULL,
    away_score          INT,
    home_team           VARCHAR(5) NOT NULL,
    home_score          INT,
    location            VARCHAR(20),
    result              INT,
    total               INT,
    overtime            INT,
    -- External game IDs
    old_game_id         VARCHAR(20),
    gsis                INT,
    pfr                 VARCHAR(30),
    espn                VARCHAR(20),
    ftn                 REAL,
    -- Rest days
    away_rest           INT,
    home_rest           INT,
    -- Betting lines
    away_moneyline      INT,
    home_moneyline      INT,
    spread_line         REAL,
    away_spread_odds    INT,
    home_spread_odds    INT,
    total_line          REAL,
    under_odds          INT,
    over_odds           INT,
    -- Game context
    div_game            INT,
    roof                VARCHAR(20),
    surface             VARCHAR(30),
    temp                REAL,
    wind                REAL,
    -- Starting QBs
    away_qb_id          VARCHAR(20),
    home_qb_id          VARCHAR(20),
    away_qb_name        VARCHAR(60),
    home_qb_name        VARCHAR(60),
    -- Coaches and officials
    away_coach          VARCHAR(60),
    home_coach          VARCHAR(60),
    referee             VARCHAR(60),
    -- Stadium
    stadium_id          VARCHAR(20),
    stadium             VARCHAR(100),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);