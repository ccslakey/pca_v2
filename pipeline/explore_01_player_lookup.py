"""
explore_01_player_lookup.py

Tests:
  - Chadwick register (GitHub) — player ID cross-reference table
  - playerid_lookup by name
  - playerid_reverse_lookup by mlbam ID
  - Lahman database (GitHub) — historical batting/pitching back to 1871

Run from project root:
  ./env/bin/python pipeline/explore_01_player_lookup.py
"""

import sys
import pybaseball
import pandas as pd

pybaseball.cache.enable()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

DIVIDER = "\n" + "=" * 70 + "\n"


def section(title):
    print(DIVIDER + title + DIVIDER)


# ---------------------------------------------------------------------------
# 1. Chadwick Register — full cross-reference table
# ---------------------------------------------------------------------------
section("1. CHADWICK REGISTER (player ID cross-reference)")

register = pybaseball.chadwick_register()
print(f"Shape: {register.shape}")
print(f"Columns: {list(register.columns)}")
print(f"\nSample rows:")
print(register.head(5).to_string())
print(f"\nMLB debut year range: {register['mlb_played_first'].min()} – {register['mlb_played_last'].max()}")
print(f"Rows with mlbam_id (Statcast era): {(register['key_mlbam'] > 0).sum()}")
print(f"Rows with fg_id: {(register['key_fangraphs'] > 0).sum()}")
print(f"Rows with bbref_id: {register['key_bbref'].notna().sum()}")


# ---------------------------------------------------------------------------
# 2. Player ID lookup by name
# ---------------------------------------------------------------------------
section("2. PLAYER ID LOOKUP BY NAME")

test_players = [
    ("ohtani", "shohei"),
    ("judge", "aaron"),
    ("trout", "mike"),
    ("clemens", "roger"),    # retired pre-Statcast
    ("mantle", "mickey"),    # pre-modern
]

for last, first in test_players:
    result = pybaseball.playerid_lookup(last, first)
    if result.empty:
        print(f"  {first} {last}: NOT FOUND")
    else:
        row = result.iloc[0]
        print(
            f"  {first.title()} {last.title()}: "
            f"mlbam={row['key_mlbam']} | fg={row['key_fangraphs']} | "
            f"bbref={row['key_bbref']} | retro={row['key_retro']} | "
            f"active={row['mlb_played_first']}–{row['mlb_played_last']}"
        )


# ---------------------------------------------------------------------------
# 3. Reverse lookup — from mlbam ID back to player info
# ---------------------------------------------------------------------------
section("3. REVERSE LOOKUP (mlbam IDs → player info)")

known_ids = [660271, 592450, 545361, 592789]  # Ohtani, Judge, Trout, Scherzer
result = pybaseball.playerid_reverse_lookup(known_ids, key_type='mlbam')
print(result[['name_last', 'name_first', 'key_mlbam', 'key_fangraphs', 'key_bbref',
              'mlb_played_first', 'mlb_played_last']].to_string())


# ---------------------------------------------------------------------------
# 4. Lahman — historical batting (back to 1871)
# ---------------------------------------------------------------------------
section("4. LAHMAN BATTING (historical, 1871–present)")

batting = pybaseball.lahman.batting()
print(f"Shape: {batting.shape}")
print(f"Columns: {list(batting.columns)}")
print(f"Year range: {batting['yearID'].min()} – {batting['yearID'].max()}")
print(f"\nSample — modern (2023 Aaron Judge):")
judge_lahman = batting[(batting['yearID'] == 2023) & (batting['playerID'].str.startswith('judgaar'))]
print(judge_lahman.to_string() if not judge_lahman.empty else "  (not found by prefix — check playerID format)")

print(f"\nSample — vintage (1927):")
print(batting[batting['yearID'] == 1927].head(3).to_string())

print(f"\nColumns with NaN in modern seasons (2020–2024):")
modern = batting[batting['yearID'] >= 2020]
null_pct = (modern.isnull().sum() / len(modern) * 100).round(1)
print(null_pct[null_pct > 0].to_string())


# ---------------------------------------------------------------------------
# 5. Lahman — historical pitching
# ---------------------------------------------------------------------------
section("5. LAHMAN PITCHING (historical, 1871–present)")

pitching = pybaseball.lahman.pitching()
print(f"Shape: {pitching.shape}")
print(f"Columns: {list(pitching.columns)}")
print(f"Year range: {pitching['yearID'].min()} – {pitching['yearID'].max()}")
print(f"\nSample — 1927:")
print(pitching[pitching['yearID'] == 1927].head(3).to_string())

print(f"\nWhat Lahman LACKS (not in columns):")
missing = ["WAR", "FIP", "xFIP", "SIERA", "wOBA", "wRC+", "BABIP_advanced", "K%", "BB%"]
for stat in missing:
    print(f"  - {stat}")


# ---------------------------------------------------------------------------
# 6. Lahman — People table (biographical data)
# ---------------------------------------------------------------------------
section("6. LAHMAN PEOPLE (biographical data)")

people = pybaseball.lahman.people()
print(f"Shape: {people.shape}")
print(f"Columns: {list(people.columns)}")
print(f"\nSample:")
print(people.head(3).to_string())


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section("SUMMARY")
print("""
DATA SOURCES (no FanGraphs required):

  Chadwick Register:
    - Player ID cross-reference: mlbam ↔ fangraphs ↔ bbref ↔ retrosheet
    - ~20k+ MLB players, 1871–present
    - Pulled from GitHub (chadwickbureau/register)

  Lahman Database (chadwickbureau/baseballdatabank):
    - Counting stats only: G, AB, H, 2B, 3B, HR, RBI, BB, SO, SB, ERA, W, L, IP, SO...
    - NO advanced stats: no WAR, FIP, wOBA, wRC+, K%, BB%, BABIP
    - Year range: 1871–present (updated annually)
    - Good for historical pre-Statcast context

  What is MISSING without FanGraphs:
    - Season-level WAR, FIP, xFIP, SIERA, wOBA, wRC+, BABIP, K%, BB%
    - Split stats (vs LHP/RHP, home/away)
    - Sprint speed context tied to season stats
    - These are ONLY available via FanGraphs or Baseball Reference scraping
""")
