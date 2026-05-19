"""
explore_02_statcast_pitchlevel.py

Tests Baseball Savant pitch-level Statcast data:
  - statcast_batter() — pitch-by-pitch for a batter
  - statcast_pitcher() — pitch-by-pitch for a pitcher
  - statcast_single_game()
  - Tests historical depth: how far back does Statcast go?
  - Column audit: what fields are present / null rates

Run from project root:
  ./env/bin/python pipeline/explore_02_statcast_pitchlevel.py
"""

import pybaseball
import pandas as pd
import time

pybaseball.cache.enable()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

DIVIDER = "\n" + "=" * 70 + "\n"

# Known MLBAM IDs
OHTANI   = 660271
JUDGE    = 592450
TROUT    = 545361
SCHERZER = 592789
DEGROM   = 594798


def section(title):
    print(DIVIDER + title + DIVIDER)


def audit_columns(df, label):
    """Print column names, dtypes, and null % for a DataFrame."""
    print(f"\n{label}")
    print(f"  Shape: {df.shape}")
    null_pct = (df.isnull().sum() / len(df) * 100).round(1)
    info = pd.DataFrame({
        'dtype': df.dtypes,
        'null_%': null_pct,
        'sample': df.iloc[0] if len(df) > 0 else None,
    })
    print(info.to_string())


# ---------------------------------------------------------------------------
# 1. Batter pitch-level — recent season
# ---------------------------------------------------------------------------
section("1. STATCAST BATTER — recent season (Ohtani 2024)")

t0 = time.time()
df_ohtani = pybaseball.statcast_batter('2024-03-20', '2024-09-29', player_id=OHTANI)
print(f"Fetched in {time.time()-t0:.1f}s")

if df_ohtani is not None and not df_ohtani.empty:
    print(f"Rows: {len(df_ohtani)}")
    print(f"Date range in data: {df_ohtani['game_date'].min()} – {df_ohtani['game_date'].max()}")
    print(f"\nAll columns ({len(df_ohtani.columns)}):")
    print(list(df_ohtani.columns))

    # Chart-relevant columns audit
    chart_cols = [
        'game_date', 'pitch_type', 'release_speed', 'release_spin_rate',
        'pfx_x', 'pfx_z', 'plate_x', 'plate_z', 'launch_speed', 'launch_angle',
        'hit_distance_sc', 'events', 'description', 'zone',
        'estimated_ba_using_speedangle', 'estimated_woba_using_speedangle',
        'hc_x', 'hc_y', 'balls', 'strikes', 'inning', 'home_team', 'away_team',
        'at_bat_number', 'pitch_number', 'game_pk', 'batter', 'pitcher',
        'bb_type', 'stand', 'p_throws',
    ]
    present = [c for c in chart_cols if c in df_ohtani.columns]
    missing = [c for c in chart_cols if c not in df_ohtani.columns]
    print(f"\nChart columns present ({len(present)}/{len(chart_cols)}): {present}")
    print(f"Chart columns MISSING: {missing}")

    print(f"\nPitch type distribution:")
    print(df_ohtani['pitch_type'].value_counts().to_string())

    print(f"\nNull rates for key columns:")
    key_cols = [c for c in chart_cols if c in df_ohtani.columns]
    null_pct = (df_ohtani[key_cols].isnull().sum() / len(df_ohtani) * 100).round(1)
    print(null_pct[null_pct > 0].to_string())

    print(f"\nSample row (first pitch):")
    print(df_ohtani[key_cols].iloc[0].to_string())
else:
    print("ERROR: empty or None result")


# ---------------------------------------------------------------------------
# 2. Historical depth test — Statcast batter
# ---------------------------------------------------------------------------
section("2. STATCAST HISTORICAL DEPTH TEST (batter)")

years_to_test = [
    ("2024", "2024-04-01", "2024-04-07"),
    ("2022", "2022-04-01", "2022-04-07"),
    ("2020", "2020-07-23", "2020-07-30"),  # COVID shortened season start
    ("2017", "2017-04-01", "2017-04-07"),
    ("2015", "2015-04-05", "2015-04-12"),  # First Statcast season
    ("2014", "2014-04-01", "2014-04-07"),  # Pre-Statcast — should be empty
]

for label, start, end in years_to_test:
    try:
        df = pybaseball.statcast_batter(start, end, player_id=TROUT)
        rows = len(df) if df is not None else 0
        cols = len(df.columns) if df is not None and not df.empty else 0
        has_launch = 'launch_speed' in df.columns if df is not None and not df.empty else False
        has_spin   = 'release_spin_rate' in df.columns if df is not None and not df.empty else False
        print(f"  {label} ({start} – {end}): {rows} rows | {cols} cols | launch_speed={has_launch} | spin_rate={has_spin}")
    except Exception as e:
        print(f"  {label}: ERROR — {e}")


# ---------------------------------------------------------------------------
# 3. Pitcher pitch-level
# ---------------------------------------------------------------------------
section("3. STATCAST PITCHER — recent season (deGrom 2022, injury year)")

t0 = time.time()
df_pitcher = pybaseball.statcast_pitcher('2022-04-07', '2022-09-29', player_id=DEGROM)
print(f"Fetched in {time.time()-t0:.1f}s")

if df_pitcher is not None and not df_pitcher.empty:
    print(f"Rows: {len(df_pitcher)}")
    print(f"Date range: {df_pitcher['game_date'].min()} – {df_pitcher['game_date'].max()}")
    print(f"\nPitch type distribution:")
    print(df_pitcher['pitch_type'].value_counts().to_string())

    # Arsenal summary
    print(f"\nArsenal by pitch type (mean velo + spin):")
    arsenal = df_pitcher.groupby('pitch_type').agg(
        count=('release_speed', 'count'),
        avg_velo=('release_speed', 'mean'),
        avg_spin=('release_spin_rate', 'mean'),
        avg_pfx_x=('pfx_x', 'mean'),
        avg_pfx_z=('pfx_z', 'mean'),
    ).round(1)
    print(arsenal.to_string())
else:
    print("ERROR: empty or None result")


# ---------------------------------------------------------------------------
# 4. Single game test
# ---------------------------------------------------------------------------
section("4. STATCAST SINGLE GAME")

# 2024 ALCS Game 4, Yankees vs Guardians — game_pk 745528
GAME_PK = 745528
try:
    df_game = pybaseball.statcast_single_game(GAME_PK)
    if df_game is not None and not df_game.empty:
        print(f"Game pk {GAME_PK}: {len(df_game)} pitches")
        print(f"Teams: {df_game['away_team'].iloc[0]} @ {df_game['home_team'].iloc[0]}")
        print(f"Date: {df_game['game_date'].iloc[0]}")
        print(f"Pitchers: {df_game['pitcher'].unique()}")
    else:
        print("Empty result — game_pk may be wrong or not in Statcast")
except Exception as e:
    print(f"ERROR: {e}")


# ---------------------------------------------------------------------------
# 5. Key fields for spray charts / pitch location maps
# ---------------------------------------------------------------------------
section("5. SPRAY CHART & PITCH LOCATION FIELDS (Ohtani 2024)")

if df_ohtani is not None and not df_ohtani.empty:
    spray_fields = ['hc_x', 'hc_y', 'launch_speed', 'launch_angle', 'hit_distance_sc',
                    'events', 'bb_type', 'estimated_ba_using_speedangle']
    available = [c for c in spray_fields if c in df_ohtani.columns]
    batted_balls = df_ohtani[df_ohtani['events'].notna()][available]
    print(f"Batted ball events (non-null events): {len(batted_balls)}")
    print(f"\nNull rates in batted ball subset:")
    print((batted_balls.isnull().sum() / len(batted_balls) * 100).round(1).to_string())
    print(f"\nSample batted balls (first 5):")
    print(batted_balls.head(5).to_string())

    # Pitch location fields
    print(f"\nPitch location sample (plate_x, plate_z, zone):")
    loc_cols = ['pitch_type', 'plate_x', 'plate_z', 'zone', 'description', 'release_speed']
    loc_cols = [c for c in loc_cols if c in df_ohtani.columns]
    print(df_ohtani[loc_cols].head(10).to_string())


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section("SUMMARY")
print("""
STATCAST PITCH-LEVEL DATA:

  Source: Baseball Savant (baseballsavant.mlb.com)
  Coverage: 2015 – present (first Statcast season was 2015)
  Pre-2015: Returns empty DataFrame — no pitch-level data available

  Key available fields:
    Identity:    game_pk, game_date, batter (mlbam), pitcher (mlbam),
                 at_bat_number, pitch_number, home_team, away_team
    Pitch:       pitch_type, release_speed, release_spin_rate,
                 pfx_x, pfx_z (movement), plate_x, plate_z, zone
    Batted ball: launch_speed, launch_angle, hit_distance_sc,
                 hc_x, hc_y (spray coords), bb_type, events
    Expected:    estimated_ba_using_speedangle (xBA),
                 estimated_woba_using_speedangle (xwOBA)
    Situational: balls, strikes, inning, stand, p_throws

  Limitations:
    - No spin rate before 2015
    - No xBA/xwOBA before ~2017 (Statcast camera upgrade)
    - hc_x / hc_y (hit coordinates) may be null on non-contact pitches
    - release_spin_rate can be null on older 2015-2016 data
""")
