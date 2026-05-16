# Data Sources & Freshness

---

## Primary sources

| Data | Source | Coverage |
|---|---|---|
| Season batting stats | Baseball Reference via pybaseball | 1871–present |
| Season pitching stats | Baseball Reference via pybaseball | 1871–present |
| Season fielding stats | Baseball Reference via pybaseball | 1871–present |
| Player bio (debut, final game, handedness, position) | Baseball Reference via pybaseball | 1871–present |
| Award history | Baseball Reference (scraped) | Per award's first year of existence |
| Pitch zone data | Baseball Savant (Statcast) via pybaseball | 2015–present |

Baseball Reference does not offer a public API. Data is scraped using the pybaseball library, which wraps their public-facing HTML tables. Sports Reference (BBref's parent) has published rate limits; our pipeline respects a delay of ~3.5 seconds between requests to stay well under the documented 20-requests-per-minute ceiling.

---

## Update cadence

| Data type | Update frequency |
|---|---|
| Batting and pitching season stats | Weekly during the season (Mondays) |
| Pitch zone heatmaps | Weekly during the season, after stats update |
| Award records | Once per year (November, after postseason awards are announced) |
| Similarity vectors | Recomputed after every stats update |

During the offseason, stats are updated once after the final transaction cycle completes and year-end figures are certified by Baseball Reference (typically December–January).

### Data lag

Baseball Reference typically finalizes game-level stats 2–3 days after each game. Running weekly on Mondays means the most recent data on the site is usually 2–4 days old during the season, and up to 7 days old at the end of a refresh cycle.

The footer on every page shows the date of the most recent stats update.

---

## What's not included

- **Minor league statistics** — not in scope. Players are tracked from their MLB debut only.
- **International league data** (NPB, KBO, etc.) — not included.
- **Projected statistics** — this site shows historical data only, no projections.
- **Real-time pitch-by-pitch data** — the Statcast zone data is aggregated per season, not live.
- **Salary data** — not tracked.

---

## On pybaseball and third-party data

pybaseball is an open-source Python library that scrapes Baseball Reference and Baseball Savant. It is a third-party tool with no official affiliation with Sports Reference or MLB. If Sports Reference changes their HTML structure, pybaseball may silently return empty data or raise parse errors. Our pipeline validates row counts after each fetch to catch silent failures.

All data on this site is derived from publicly available sources. We do not redistribute raw data or claim any intellectual property rights over the statistics themselves.
