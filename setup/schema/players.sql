-- Players: master player lookup table sourced from nflverse.
-- Primary key is gsis_id, the NFL's Game Statistics & Information System ID.
-- Cross-platform IDs retained for potential joins with external data sources.
--
-- Columns dropped from nflreadpy output:
--   common_first_name            — redundant with first_name
--   short_name                   — redundant name variant (69.8% null)
--   football_name                — redundant name variant (67.9% null)
--   suffix                       — nearly always null (99.3% null)
--   ngs_position_group           — NGS-specific position grouping (79.3% null)
--   ngs_position                 — NGS-specific position (79.6% null)
--   headshot                     — image URL, not needed in database
--   ngs_status                   — NGS-specific status field (67.9% null)
--   ngs_status_short_description — NGS-specific status abbreviation (74.5% null)
--   pff_position                 — PFF-specific position (69.5% null)
--   pff_status                   — PFF-specific status (84.2% null)

CREATE TABLE IF NOT EXISTS players (
    gsis_id             VARCHAR(20) PRIMARY KEY,
    display_name        VARCHAR(100) NOT NULL,
    first_name          VARCHAR(50) NOT NULL,
    last_name           VARCHAR(50) NOT NULL,
    position            VARCHAR(10) NOT NULL,
    position_group      VARCHAR(10) NOT NULL,
    jersey_number       VARCHAR(5),
    height              REAL,
    weight              REAL,
    birth_date          VARCHAR(20),
    college_name        VARCHAR(100),
    college_conference  VARCHAR(100),
    rookie_season       INT NOT NULL,
    last_season         INT NOT NULL,
    latest_team         VARCHAR(5) NOT NULL,
    status              VARCHAR(10) NOT NULL,
    years_of_experience INT NOT NULL,
    draft_year          REAL,
    draft_round         REAL,
    draft_pick          REAL,
    draft_team          VARCHAR(5),
    -- Cross-platform IDs
    esb_id              VARCHAR(20),
    nfl_id              VARCHAR(20),
    pfr_id              VARCHAR(20),
    pff_id              VARCHAR(20),
    otc_id              VARCHAR(20),
    espn_id             VARCHAR(20),
    smart_id            VARCHAR(50),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);