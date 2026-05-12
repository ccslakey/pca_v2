# Feature Roadmap

Living doc. Update as priorities shift or features ship.

---

## Shipped

- **Leaderboard / Browse page** — filterable, sortable table; position, era, WAR filters; award badge tooltips on hover
- **Browse Players link in TopBar** — navigation entry point from the compare chart
- **Shareable multi-player comparison URLs** — `?compare=ruthba01,youngcy01` syncs to URL on every add/remove, parses on load; commas unencoded
- **Award glyphs on compare chart** — circled icons on chart lines for all 13 award kinds (MVP, Cy Young, Gold Glove, All-Star, World Series, Silver Slugger, ERA Title, batting title, Triple Crown, etc.); priority system shows the rarest award when multiple fall in the same year; show/hide toggle to the left of the legend
- **Age / Calendar X-axis toggle** — align players by career age instead of calendar year for cross-era comparison; brush resets to full range on toggle or when a new player is added
- **Player bio DateFields** — replaced `birth_year` integer with `birth_date` DateField; `debut` and `final_game` stored as dates end-to-end (Django DateField → ISO string API → `getUTCFullYear()` in frontend); backfill script populated 22,163 birth dates from Lahman People.csv
- **Monthly heatmap cut** — removed; generated fake data from a seeded RNG which is a credibility hit in a data tool; needs real monthly splits before it can return
- **Player position data** — `FieldingSeason` model, `primary_position` on `Player`, position-based leaderboard filtering, serializer/view updates

---

## Known Integrity Issues (fix before public launch)

### Monthly heatmap (cut pending real data)
No real monthly breakdown in the current data model. Real data options:
- Ingest monthly splits from Baseball Reference or Statcast (Statcast has month-level for 2015+)
- Until then: panel is removed

---

## Priority 1 — Fast Analytical Wins

All of these use only data already in the DB — no new ingestion required.

### HOF Monitor + Black Ink + Gray Ink (Bill James scores)
Three classic sabermetric scores that are pure SQL aggregations over existing season data:
- **Black Ink** — points for leading the league in standard categories each year
- **Gray Ink** — points for finishing top 10
- **HOF Monitor** — weighted score (MVPs, batting titles, milestones, career rates) designed to predict HOF election

Reduces to "rank each league-year, sum points." High analytical credibility, sits naturally on the profile next to career WAR. Strongest portfolio signal in this section.

### Percentile rankings
Show context next to every career stat: "Career WAR ranks 12th all-time among CF" or "top 3% of all pitchers by ERA".

- Compute at query time or precompute into a `career_percentiles` table
- Surface on the stat grid in the profile page (small badge or tooltip)
- Now that `primary_position` exists, percentiles by position become possible

### Career milestone overlay on the compare chart
Mark the season when a player crossed 500 HR / 3000 H / 300 W / 3000 K / 2000 RBI etc. as labeled markers on the career arc. Year-by-year cumulative totals are already derivable; just precompute crossings.

### Team timeline on the profile
A horizontal stripe showing which teams the player played for and when, derived from the `team` field on BattingSeason/PitchingSeason. One pass over the season log; zero new fields.

### Career rate-stat slash line in the hero
Career AVG/OBP/SLG/OPS (or ERA/WHIP/K9 for pitchers) computed from existing totals. Many profiles likely don't surface this yet despite the data being available.

### Year-by-year league leadership badges
For each season in the season-log panel, add small "1st" / "T-2nd" badges next to WAR, HR, ERA, etc. when the player led/co-led the league. Pure ranking query within (year, league). Polish-tier — useful but lower analytical signal than the rest.

---

## Priority 2 — Analytical Depth (resume differentiators)

### Era-adjusted stats
Raw batting average and ERA are not comparable across eras. Normalizing stats to a common baseline makes cross-era comparisons meaningful.

- Requires league-average stats per year (derivable from existing season data)
- Surface as a toggle: "raw" vs "era-adjusted" on the career arc and stat grid
- OPS+ and ERA+ are already ingested — could surface those directly as a first pass

### "Similar through age N" — career-stage similarity
Extend the similarity engine to support comps at any career stage, not just career totals. BBref's similarity tool exposes both — "similar through age N" is the canonical prospect-comp question (e.g. "who was Mike Trout most like at 24?"). Currently we only do career totals.

- Swap the career aggregations in `_load_*_agg()` for seasonal totals truncated at age N
- Surface as a slider or dropdown on the similar-players panel
- See [`SIMILARITY.md`](SIMILARITY.md) for the full gap list

### Aging curve overlay with documented methodology
Show a player's career arc against the positional average aging curve.

- Compute average WAR-by-age for each position group across all players in the DB
- Overlay as a shaded band or dashed line on the career arc chart
- Document smoothing applied, minimum PA/IP thresholds, how survivorship bias is handled
- Pairs naturally with the existing age/calendar toggle

### Stuff+ implementation
Pitch-quality metric measuring expected whiffs and weak contact, holding location constant.

- Requires Statcast pitch-level data (pitch type, velocity, spin rate, movement, release point)
- Model: regress whiff rate on pitch characteristics within pitch-type buckets
- Output: per-pitch-type Stuff+ score normalized to 100 = league average

### Pitch arsenal analysis
Profile each pitcher's full mix — not just individual pitch grades, but how the arsenal functions as a unit.

- Usage rates by count, platoon, leverage
- Movement profile plots (horizontal vs. vertical break)
- Tunnel analysis: do pitches share a release window before diverging?

### WAR decomposition (data ingest)
Break career WAR into components on the profile page: batting runs, fielding runs, baserunning runs, positional adjustment.

- Baseball Reference exposes these in the detailed season tables
- Would require additional ingest columns

---

## Priority 3 — Ambitious / Differentiating

### Natural language player search
"Find me pitchers like Sandy Koufax but modern era" or "dominant lefties with short careers".

- The similarity embedding model already exists — this is a query interface on top of it
- Could use an LLM to parse the query into filters + a similarity anchor

### Player projection system
Given a player's career arc to date, project performance for the next 1–3 seasons.

- Anchor to the aging curve: expected decline rate by age and position
- Regression-to-the-mean on rate stats (BABIP, strand rate, etc.)
- Confidence intervals widen with each projected year
- Pairs with the aging curve overlay

### Hall of Fame probability
Given a player's career trajectory at age X, what's the probability they reach Cooperstown?

- Logistic regression on career WAR, peak WAR, awards, longevity as a baseline
- Show as a career-stage progress indicator on the profile page

---

## Production Deployment

### Full production deployment with pipeline documentation

**What it takes:**
- Containerize backend + frontend (Docker Compose, or separate services)
- CI/CD pipeline: tests on PR, deploy on merge to main
- Environment config: secrets management, prod database, CORS settings
- Data pipeline docs: what data comes from where, ingest frequency, how to re-run from scratch

**Platform:** Render or Railway for the app; Neon or Supabase for Postgres.

---

## Scheduled Data Jobs

See [`SCHEDULED_JOBS.md`](SCHEDULED_JOBS.md) for the full breakdown.

**What needs scheduling:**
- Weekly stats refresh (BattingSeason, PitchingSeason, StatcastZoneBucket)
- Season-start pass for new players and rookies
- Post-season awards ingest (November)
- Similarity vector recompute after every stats update

**Three requirements for a trustworthy cron system:**
1. **Failure alerting** — a silent failure that leaves stale data is worse than no job at all
2. **Staleness detection** — the API should expose `last_updated` so stale data is visible in the UI
3. **Dependency ordering** — similarity vectors must recompute *after* the stats update completes

---

## Deferred / Won't Do Soon

- Platoon splits (vs LHP / RHP) — needs more granular data
- WPA / clutch stats — needs play-by-play data
- Export to PNG — nice-to-have, not core
- Mobile layout — currently desktop-only, not blocking for a portfolio tool

### xBA / xERA from first principles
Build own expected batting average and ERA models rather than consuming Baseball Savant's published numbers. High methodological value, low demo value — requires full pitch-level Statcast ingest and the output won't visually differ from Savant's numbers. Better to explain the methodology gap in interviews.

### WAR decomposition from first principles
Reconstruct WAR from linear weights rather than using bWAR/fWAR directly. bWAR and fWAR regularly disagree by 1–3 WAR due to different defensive metrics, positional adjustments, and park factors. Building your own forces each choice to be explicit — but substantial modeling work with diminishing visual return for a portfolio tool.
