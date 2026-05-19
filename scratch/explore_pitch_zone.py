"""
Pitch Zone Heatmap — design exploration
========================================

GOAL
----
Render a pitch-location heatmap per player (catcher's view) showing
where batters make contact / whiff, and where pitchers induce whiffs /
get hit.  Toggle between two outcome layers (e.g. Contact vs Whiffs).

DATA SOURCE: Baseball Savant (Statcast) via pybaseball
------------------------------------------------------
pybaseball.statcast_batter(start_dt, end_dt, mlbam_id)  → batter pitches
pybaseball.statcast_pitcher(start_dt, end_dt, mlbam_id) → pitcher pitches

Coverage : 2015-present
Cost     : 1 API call per player (career pull, 2015–present)
           ~22 s per player; ~14k rows for a 7-yr career
           Aggregate on ingest → store only grid cell counts
Key cols : plate_x  (horiz, feet from center; negative = inside for RHB)
           plate_z  (vert, feet above ground)
           sz_top   (batter-specific zone top, median ~3.47)
           sz_bot   (batter-specific zone bot, median ~1.58)
           description: 'swinging_strike', 'called_strike',
                        'hit_into_play', 'foul', 'ball', ...
           events  : 'single', 'double', 'home_run', 'strikeout', ...
           stand   : 'R' | 'L'  (batter handedness)
           p_throws: 'R' | 'L'  (pitcher handedness)

Requires : mlbam_id on Player model (already stored)
Caveat   : pre-2015 players show no data; show "Statcast era only" label

COORDINATE SYSTEM
-----------------
Catcher's view (same as in the screenshot):
  plate_x: negative = batter's inside (left side of screen for RHB)
           positive = batter's outside (right side of screen for RHB)
  plate_z: higher = up

Fixed render bounds (feet):
  x: -2.0 to +2.0  (4-foot width, covers zone + chase pitches)
  z:  0.5 to  5.0  (4.5-foot height)

Standard strike zone within those bounds:
  x: -0.83 to +0.83  (17 inches ÷ 2, per MLB rules)
  z: sz_bot to sz_top  (player-specific; use fixed 1.5 / 3.5 for display)

COORDINATE STORAGE
------------------
Backend stores raw plate_x / plate_z aggregated at 0.1 ft resolution.
Frontend receives (plate_x, plate_z, count, total) buckets and bins them
into whatever grid resolution it wants at render time.

Advantages:
  - Grid resolution is a frontend concern; no re-ingest needed to change it
  - More grid cells = more accurate hotspot placement (blurred SVG looks
    sharper at 15×15 than 9×9 for the same blur radius)
  - Frontend applies min-count threshold (e.g. total >= 5) to suppress
    sparse cells; the rest are coloured normally

Recommended frontend grid: 15 × 15
  cell_width  = 4.0 / 15 ≈ 0.27 ft
  cell_height = 4.5 / 15 = 0.30 ft
  blur stdDeviation ≈ 1.5 cells (in SVG user units)

At ~14k career pitches, 15×15 = 225 cells → ~62 pitches/cell average,
well above the noise floor even for sparse zones.

plate_x is NOT mirrored for handedness.  Catcher's view is rendered
as-is from Statcast coordinates.  Lefties and righties will naturally
differ, which is accurate.

OUTCOME LAYERS (toggle in UI)
------------------------------
Batters:
  'contact'  — description == 'hit_into_play' (all contact)
  'hits'     — events in {'single','double','triple','home_run'}
  'whiffs'   — description in {'swinging_strike','swinging_strike_blocked'}

Pitchers (same data, viewed from pitcher perspective):
  'whiffs'   — swinging strikes induced
  'hard_hit' — hit_into_play where launch_speed >= 95 mph (if available)
  'contact'  — all balls put in play

Normalize counts to rate per 100 pitches in that cell for
cross-player comparability.

DATA MODEL
----------
class StatcastZoneBucket(models.Model):
    player   = ForeignKey(Player, on_delete=CASCADE, related_name='zone_buckets')
    role     = CharField(max_length=1)    # 'B' batter | 'P' pitcher
    outcome  = CharField(max_length=10)   # 'contact' | 'hits' | 'whiffs'
    plate_x  = FloatField()              # raw Statcast x, rounded to 0.1 ft
    plate_z  = FloatField()              # raw Statcast z, rounded to 0.1 ft
    count    = IntegerField()            # pitches with this outcome at (x, z)
    total    = IntegerField()            # total pitches seen at (x, z)

    class Meta:
        unique_together = ('player', 'role', 'outcome', 'plate_x', 'plate_z')
        indexes = [Index(fields=['player', 'role', 'outcome'])]

Storage estimate:
  ~500–800 occupied (x, z) buckets per player across all outcomes
  3 outcomes × ~600 buckets = ~1,800 rows per player
  800 players → ~1.4 M rows total — well within PostgreSQL comfort zone

INGEST SCRIPT
-------------
pipeline/ingest_statcast_zones.py

Approach:
  1. Query Player.objects.filter(mlbam_id__isnull=False)
     optionally filter: only players with mlb_played_last >= 2015
     optionally filter: career WAR threshold (e.g. 10+ to start)
  2. For each player:
       if batter: statcast_batter('2015-03-01', TODAY, mlbam_id)
       if pitcher: statcast_pitcher('2015-03-01', TODAY, mlbam_id)
       two-way players: both
  3. Filter rows where plate_x / plate_z are not null
  4. Map each pitch to (cell_x, cell_z) using fixed bounds
  5. Tally count and total per (cell_x, cell_z, outcome)
  6. bulk_create(PitchZoneCell rows, update_conflicts=True)
  7. Log to IngestionLog: key = 'statcast_zone_batter_{bbref_id}'
  8. Respect BRef session rate limiting via time.sleep between calls
     (Statcast is separate from BRef but pybaseball adds its own throttle)

Estimated cost:
  Players with mlbam_id + mlb_played_last >= 2015: ~4,000–5,000
  At ~25 s/player + overhead: 100,000 s ≈ 28 hours unthrottled
  → Prioritise by career WAR: top 500 batters + top 300 pitchers
  → At 800 players × 25 s = 20,000 s ≈ 5–6 hours (run overnight)

API ENDPOINT
------------
GET /api/players/{bbref_id}/pitch_zone/?role=B&outcome=contact

Returns:
  {
    "role": "B",
    "outcome": "contact",
    "grid_size": 9,
    "cells": [
      {"cell_x": 4, "cell_z": 6, "count": 28, "total": 62, "rate": 45.2},
      ...
    ]
  }

FRONTEND COMPONENT: PitchZone
------------------------------
Props: { cells: ZoneCell[], gridSize: number, width: number, height: number }

Render approach — blurred SVG rects (matches screenshot style):
  1. Draw 9×9 colored rect grid, color = interpolate(blue→red) by rate
  2. Apply SVG <feGaussianBlur> filter (stdDeviation ~1.5 cell widths)
     to get the smooth radial blur look
  3. Overlay dashed strike zone rectangle (fixed pixel bounds)
  4. Add UP/DOWN/IN/AWAY labels at edges
  5. Toggle button (Contact / Whiffs) switches `outcome` query param

No extra npm packages needed — pure SVG + existing Visx color interpolation.

OPEN QUESTIONS
--------------
- plate_x NOT mirrored — catcher's view rendered as raw Statcast coords
- Show per-season selector, or career aggregate only?
  → Career aggregate first; season filter is a nice follow-on
- Min pitch threshold per cell to avoid noise?
  → Frontend hides cells where total < 5; colour scale anchored to
    visible cells only so sparse zones don't dominate the range
- Two-way players (Ohtani): show both B and P tabs
- Frontend grid resolution: 15×15 recommended; could expose as prop
"""
