"""
explore_03_savant_leaderboards.py

Tests all Baseball Savant leaderboard endpoints (no FanGraphs):
  - statcast_batter_exitvelo_barrels()
  - statcast_batter_expected_stats()
  - statcast_batter_percentile_ranks()
  - statcast_batter_pitch_arsenal()
  - statcast_pitcher_exitvelo_barrels()
  - statcast_pitcher_expected_stats()
  - statcast_pitcher_pitch_arsenal()
  - statcast_pitcher_pitch_movement()
  - statcast_pitcher_active_spin()
  - statcast_pitcher_percentile_ranks()
  - statcast_sprint_speed()
  - statcast_outs_above_average()

Also tests historical depth for each leaderboard (earliest available year).

Run from project root:
  ./env/bin/python pipeline/explore_03_savant_leaderboards.py
"""

import pybaseball
import pandas as pd
import time

pybaseball.cache.enable()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

DIVIDER = "\n" + "=" * 70 + "\n"

OHTANI_MLBAM = 660271


def section(title):
    print(DIVIDER + title + DIVIDER)


def probe(label, func, *args, **kwargs):
    """Call a leaderboard func, print shape + columns + sample row."""
    try:
        t0 = time.time()
        df = func(*args, **kwargs)
        elapsed = time.time() - t0
        if df is None or df.empty:
            print(f"  [{label}] EMPTY ({elapsed:.1f}s)")
            return None
        print(f"  [{label}] {df.shape[0]} rows × {df.shape[1]} cols ({elapsed:.1f}s)")
        print(f"    Columns: {list(df.columns)}")
        if 'player_name' in df.columns:
            print(f"    Sample player: {df['player_name'].iloc[0]}")
        elif 'last_name' in df.columns:
            name_col = 'last_name'
            fn_col = 'first_name' if 'first_name' in df.columns else None
            print(f"    Sample player: {df[name_col].iloc[0]}" + (f", {df[fn_col].iloc[0]}" if fn_col else ""))
        return df
    except Exception as e:
        print(f"  [{label}] ERROR: {e}")
        return None


def depth_test(label, func, years, *extra_args, **kwargs):
    """Test how far back a leaderboard goes."""
    print(f"\nDepth test: {label}")
    for year in years:
        try:
            t0 = time.time()
            df = func(year, *extra_args, **kwargs)
            elapsed = time.time() - t0
            rows = len(df) if df is not None else 0
            print(f"  {year}: {rows} rows ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  {year}: ERROR — {e}")


# ---------------------------------------------------------------------------
# 1. Batter Exit Velocity / Barrels leaderboard
# ---------------------------------------------------------------------------
section("1. BATTER EXIT VELOCITY & BARRELS LEADERBOARD")
df_batter_ev = probe("batter_exitvelo_barrels 2024", pybaseball.statcast_batter_exitvelo_barrels, 2024, minBBE=50)
depth_test("batter_exitvelo_barrels", pybaseball.statcast_batter_exitvelo_barrels,
           [2024, 2022, 2020, 2017, 2015, 2014], minBBE=50)

if df_batter_ev is not None and not df_batter_ev.empty:
    # Show Ohtani's row if present
    ohtani_row = df_batter_ev[df_batter_ev['player_id'] == OHTANI_MLBAM] if 'player_id' in df_batter_ev.columns else pd.DataFrame()
    if not ohtani_row.empty:
        print(f"\n  Ohtani 2024 exit velo stats:")
        print(ohtani_row.to_string())


# ---------------------------------------------------------------------------
# 2. Batter Expected Stats (xBA, xSLG, xwOBA, xOBP)
# ---------------------------------------------------------------------------
section("2. BATTER EXPECTED STATS LEADERBOARD (xBA, xwOBA)")
df_batter_xstats = probe("batter_expected_stats 2024", pybaseball.statcast_batter_expected_stats, 2024, minPA=100)
depth_test("batter_expected_stats", pybaseball.statcast_batter_expected_stats,
           [2024, 2022, 2020, 2017, 2015], minPA=100)


# ---------------------------------------------------------------------------
# 3. Batter Percentile Rankings
# ---------------------------------------------------------------------------
section("3. BATTER PERCENTILE RANKINGS")
df_batter_pct = probe("batter_percentile_ranks 2024", pybaseball.statcast_batter_percentile_ranks, 2024)
depth_test("batter_percentile_ranks", pybaseball.statcast_batter_percentile_ranks,
           [2024, 2022, 2020, 2018])

if df_batter_pct is not None and not df_batter_pct.empty:
    print(f"\n  Percentile rank columns: {list(df_batter_pct.columns)}")


# ---------------------------------------------------------------------------
# 4. Batter Pitch Arsenal Stats (batter outcomes vs pitch type)
# ---------------------------------------------------------------------------
section("4. BATTER PITCH ARSENAL STATS")
df_batter_arsenal = probe("batter_pitch_arsenal 2024", pybaseball.statcast_batter_pitch_arsenal, 2024, minPA=25)
depth_test("batter_pitch_arsenal", pybaseball.statcast_batter_pitch_arsenal,
           [2024, 2022, 2020, 2017])


# ---------------------------------------------------------------------------
# 5. Pitcher Exit Velocity / Barrels (batted ball against)
# ---------------------------------------------------------------------------
section("5. PITCHER EXIT VELOCITY & BARRELS (AGAINST) LEADERBOARD")
df_pitcher_ev = probe("pitcher_exitvelo_barrels 2024", pybaseball.statcast_pitcher_exitvelo_barrels, 2024, minBBE=50)
depth_test("pitcher_exitvelo_barrels", pybaseball.statcast_pitcher_exitvelo_barrels,
           [2024, 2022, 2020, 2017, 2015], minBBE=50)


# ---------------------------------------------------------------------------
# 6. Pitcher Expected Stats
# ---------------------------------------------------------------------------
section("6. PITCHER EXPECTED STATS LEADERBOARD")
df_pitcher_xstats = probe("pitcher_expected_stats 2024", pybaseball.statcast_pitcher_expected_stats, 2024, minPA=100)
depth_test("pitcher_expected_stats", pybaseball.statcast_pitcher_expected_stats,
           [2024, 2022, 2020, 2017, 2015], minPA=100)


# ---------------------------------------------------------------------------
# 7. Pitcher Pitch Arsenal (avg speed, spin, usage%)
# ---------------------------------------------------------------------------
section("7. PITCHER PITCH ARSENAL (avg speed)")
df_pitch_arsenal_speed = probe("pitcher_pitch_arsenal speed 2024",
                                pybaseball.statcast_pitcher_pitch_arsenal, 2024, minP=100, arsenal_type="avg_speed")

section("7b. PITCHER PITCH ARSENAL (usage %)")
df_pitch_arsenal_pct = probe("pitcher_pitch_arsenal pct 2024",
                              pybaseball.statcast_pitcher_pitch_arsenal, 2024, minP=100, arsenal_type="n_")
depth_test("pitcher_pitch_arsenal", pybaseball.statcast_pitcher_pitch_arsenal,
           [2024, 2022, 2020, 2017, 2015], 100, arsenal_type="avg_speed")


# ---------------------------------------------------------------------------
# 8. Pitcher Pitch Movement
# ---------------------------------------------------------------------------
section("8. PITCHER PITCH MOVEMENT LEADERBOARD")
df_movement = probe("pitcher_pitch_movement FF 2024",
                    pybaseball.statcast_pitcher_pitch_movement, 2024, minP=100, pitch_type="FF")
depth_test("pitcher_pitch_movement", pybaseball.statcast_pitcher_pitch_movement,
           [2024, 2022, 2020, 2017, 2015], 100, pitch_type="FF")


# ---------------------------------------------------------------------------
# 9. Pitcher Active Spin
# ---------------------------------------------------------------------------
section("9. PITCHER ACTIVE SPIN")
df_spin = probe("pitcher_active_spin 2024", pybaseball.statcast_pitcher_active_spin, 2024, minP=100)
depth_test("pitcher_active_spin", pybaseball.statcast_pitcher_active_spin,
           [2024, 2022, 2020, 2019])  # spin-based only from 2020


# ---------------------------------------------------------------------------
# 10. Pitcher Percentile Rankings
# ---------------------------------------------------------------------------
section("10. PITCHER PERCENTILE RANKINGS")
df_pitcher_pct = probe("pitcher_percentile_ranks 2024", pybaseball.statcast_pitcher_percentile_ranks, 2024)
depth_test("pitcher_percentile_ranks", pybaseball.statcast_pitcher_percentile_ranks,
           [2024, 2022, 2020, 2018])


# ---------------------------------------------------------------------------
# 11. Sprint Speed (running)
# ---------------------------------------------------------------------------
section("11. SPRINT SPEED LEADERBOARD")
df_speed = probe("sprint_speed 2024", pybaseball.statcast_sprint_speed, 2024, min_opp=10)
depth_test("sprint_speed", pybaseball.statcast_sprint_speed,
           [2024, 2022, 2020, 2017, 2015], 10)


# ---------------------------------------------------------------------------
# 12. Outs Above Average (fielding)
# ---------------------------------------------------------------------------
section("12. OUTS ABOVE AVERAGE (fielding, by position)")

positions = {
    "CF (8)": 8,
    "RF (9)": 9,
    "LF (7)": 7,
    "SS (6)": 6,
    "3B (5)": 5,
    "2B (4)": 4,
    "1B (3)": 3,
}
for pos_label, pos_num in positions.items():
    probe(f"OAA {pos_label} 2024",
          pybaseball.statcast_outs_above_average, 2024, pos=pos_num, min_att=5)

depth_test("outs_above_average CF", pybaseball.statcast_outs_above_average,
           [2024, 2022, 2020, 2017, 2016], 8, min_att=5)


# ---------------------------------------------------------------------------
# 13. Pitcher Arsenal Stats (per-pitch outcome stats)
# ---------------------------------------------------------------------------
section("13. PITCHER ARSENAL OUTCOME STATS (run value, whiff%)")
df_arsenal_stats = probe("pitcher_arsenal_stats 2024", pybaseball.statcast_pitcher_arsenal_stats, 2024, minPA=25)
depth_test("pitcher_arsenal_stats", pybaseball.statcast_pitcher_arsenal_stats,
           [2024, 2022, 2020, 2018], 25)


# ---------------------------------------------------------------------------
# Final summary table
# ---------------------------------------------------------------------------
section("LEADERBOARD SUMMARY")
print("""
Endpoint                           Source           Earliest Year  Notes
---------------------------------  ---------------  -------------  -----
statcast_batter_exitvelo_barrels   Baseball Savant  2015           exit velo, barrels, hard hit%
statcast_batter_expected_stats     Baseball Savant  ~2017          xBA, xSLG, xwOBA, xOBP
statcast_batter_percentile_ranks   Baseball Savant  2018           percentile vs league
statcast_batter_pitch_arsenal      Baseball Savant  ~2018          batter outcomes by pitch type
statcast_pitcher_exitvelo_barrels  Baseball Savant  2015           batted ball against
statcast_pitcher_expected_stats    Baseball Savant  ~2017          xERA, xBA against
statcast_pitcher_pitch_arsenal     Baseball Savant  ~2018          arsenal speed/usage
statcast_pitcher_pitch_movement    Baseball Savant  2015           break x/z, extension
statcast_pitcher_active_spin       Baseball Savant  2020 (spin)    2019- for observed method
statcast_pitcher_percentile_ranks  Baseball Savant  2018
statcast_pitcher_arsenal_stats     Baseball Savant  ~2018          run value, whiff%, put-away%
statcast_sprint_speed              Baseball Savant  2015           ft/sec sprint speed
statcast_outs_above_average        Baseball Savant  2016           OAA by position (no catchers)

NOT AVAILABLE without FanGraphs:
  - Season WAR (bWAR via BRef is scrapeable but rate-limited)
  - Season FIP, xFIP, SIERA
  - Season wRC+, wOBA (season-level)
  - Season K%, BB%, GB%, LD%, FB% (FanGraphs-specific)
  - Split stats (vs L/R, home/away, monthly)
""")
