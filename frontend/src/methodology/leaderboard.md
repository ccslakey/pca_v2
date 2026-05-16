# Leaderboard & Qualification Rules

The leaderboard at `/browse` shows career and peak statistics for every player in the database who meets the minimum qualification threshold. This document explains who appears, how stats are calculated, and how the filters work.

---

## Minimum qualification threshold

A player appears in the leaderboard only if they have **career WAR ≥ 1.0** in at least one role (batting or pitching). This floor exists to exclude brief cup-of-coffee appearances — players who had one game or one season at the margins of the major leagues. At career WAR ≥ 1.0, every player shown made a meaningful, measurable contribution.

There is no minimum games played, minimum seasons, or minimum plate appearances/innings threshold beyond what WAR already implies.

---

## Career WAR

Career WAR shown in the leaderboard is the **sum of all season WAR values** in the database for that player. This includes:
- All stints with multiple teams in a season (each stint is a separate row)
- Negative seasons (below-replacement-level play reduces the career total)
- Both batting and pitching contributions for two-way players

The WAR source is bWAR from Baseball Reference. See the [WAR article](/methodology/war) for full details.

---

## Peak WAR

Peak WAR is the **highest single-season WAR value** in a player's career, across all stints. For players who appeared for multiple teams in a single season, the peak is the best individual stint, not the combined total for that year.

---

## Sorting

The leaderboard can be sorted by: career WAR, peak WAR, career home runs, and All-Star selections. Default sort is career WAR descending.

---

## Filters

### Position filter

Filters by `primary_position` — the position code assigned to each player in the database. See the [Primary Position article](/methodology/positions) for how this field is derived. Selecting a position shows only players whose primary position matches exactly.

### Era filter

Era presets filter by the player's active years. A player appears in an era if they **played at least one season within the era's date range** — specifically, if their debut year is ≤ the era's end year and their final game year is ≥ the era's start year.

Preset eras used:

| Label | Years |
|---|---|
| Dead Ball | 1900–1919 |
| Live Ball / Depression | 1920–1941 |
| Post-War | 1946–1960 |
| Expansion | 1961–1976 |
| Free Agency | 1977–1993 |
| Steroid Era | 1994–2004 |
| Post-Steroid | 2005–2014 |
| Statcast Era | 2015–present |

A player like Babe Ruth (1914–1935) appears in both Dead Ball and Live Ball era filters because his career spans both.

### Role filter

Separate filters for batters and pitchers. A player can appear in both if they qualify in both roles.
