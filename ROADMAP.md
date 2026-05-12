# Feature Roadmap

Living doc. Update as priorities shift or features ship.

---

## Known Integrity Issues (fix before public launch)

### Monthly heatmap uses fake data
`MonthlyHeatmap.tsx` generates values with a seeded RNG based on OPS. There is no real monthly breakdown in the current data model. Options:
- **Wire to real data** — ingest monthly splits from Baseball Reference or Statcast. Statcast has month-level granularity for 2015+.
- **Cut it** — remove the panel entirely until real data exists. A simulated visualization in a data tool is a credibility hit.

### Comparison URLs only support 1 player
`?compare=troutmi01` works but linking a multi-player comparison requires the user to rebuild it manually. Shareable state is table stakes for a tool people will want to send around.

---

## Priority 1 — Discovery / Onboarding

### Leaderboard / Browse page
**Problem:** new users hit a blank search field and must already know a player name. The tool is unusable without prior knowledge.

**What it needs:**
- Filterable list of players by position, era/decade, team, WAR threshold
- Sortable columns (career WAR, peak WAR, HR, ERA, etc.)
- Clicking a row opens the profile page
- Search still lives in the topbar for direct lookup

**Why it matters for resume:** it's the difference between a demo you have to narrate and one that speaks for itself.

---

## Priority 2 — Data Integrity / Model Completeness

### Player position data
The app currently has no position data — `Player` only has `bats`/`throws`. This weakens similarity matching, blocks position-based filtering on the leaderboard, and leaves the profile page unable to say "SS" or "CF".

**Plan:**
1. **`FieldingSeason` model** in `stats/` — one row per (player, year, team, stint, position), storing `games` at that position. Mirrors the BRef standard fielding table, supports multi-position players across all eras.
2. **`primary_position` on `Player`** — stored CharField (`"P"`, `"SS"`, `"CF"`, etc.), computed from career games-by-position. Pitchers default to `"P"` from PitchingSeason. Recomputed by a management command after each ingest run.
3. **`ingest_bref_fielding.py`** — same BRefSession/rate-limit/IngestionLog pattern as batting/pitching. Scrapes `/leagues/MLB/{year}-standard-fielding.shtml`. ~150 lines.
4. **`compute_primary_positions` management command** — aggregates career games by position, writes `primary_position` to each Player.
5. **Serializer + view updates** — expose `primary_position` in the player API.

**Why it matters:** positions unlock era-adjusted percentiles by position, aging curves per position group, "top SS by WAR" leaderboard filtering, and tighter similarity matching (CF vs. LF is a real distinction).

---

## Priority 3 — Fast Analytical Wins

### Percentile rankings
Show context next to every career stat: "Career WAR ranks 12th all-time among CF" or "top 3% of all pitchers by ERA".

- Compute at query time or precompute into a `career_percentiles` table
- Surface on the stat grid in the profile page (small badge or tooltip)
- Requires no new data ingestion

### Shareable multi-player comparison URLs
Extend `?compare=` to `?players=troutmi01,bondsba01,ruthba01`.

- Serialize selected player IDs into the URL on every change
- Parse on load and pre-populate the comparison
- Small change, high polish signal

---

## Priority 4 — Analytical Depth (resume differentiators)

### Era-adjusted stats
Raw batting average and ERA are not comparable across eras. Normalizing stats to a common baseline (e.g., league-average ERA+ style) makes cross-era comparisons meaningful.

- Requires league-average stats per year (easily derivable from existing season data)
- Surface as a toggle: "raw" vs "era-adjusted" on the career arc and stat grid
- Sabermetrically serious — shows understanding of why naive comparisons fail

### Aging curve overlay with documented methodology
Show a player's career arc against the positional average aging curve.

- Compute average WAR-by-age for each position group across all players in the DB
- Overlay as a shaded band or dashed line on the career arc chart
- Document the methodology explicitly: what smoothing is applied, minimum PA/IP thresholds, how survivorship bias is handled
- Immediately answers "did this player age well or decline early?"
- Visually striking, analytically meaningful

### Stuff+ implementation
Pitch-quality metric that measures how often a given pitch would be expected to generate whiffs and weak contact, holding location constant.

- Requires Statcast pitch-level data (pitch type, velocity, spin rate, movement, release point)
- Model: regress whiff rate on pitch characteristics within pitch-type buckets
- Output: per-pitch-type Stuff+ score normalized to 100 = league average
- Enables comparisons like "how did Kershaw's curveball rate against the league that year?"

### Pitch arsenal analysis
Profile each pitcher's full mix — not just how individual pitches grade, but how the arsenal functions as a unit.

- Usage rates by count, platoon, leverage
- Movement profile plots (horizontal vs. vertical break)
- Tunnel analysis: do pitches share a release window before diverging?
- Separates pitchers who throw hard from pitchers who throw smart

### WAR decomposition (data ingest)
Break career WAR into components on the profile page: batting runs, fielding runs, baserunning runs, positional adjustment.

- Baseball Reference exposes these in the detailed season tables
- Would require additional ingest columns
- Useful for answering "is this a bat-only player or a complete player?"

---

## Priority 5 — Ambitious / Differentiating

### Natural language player search
"Find me pitchers like Sandy Koufax but modern era" or "dominant lefties with short careers".

- The similarity embedding model already exists — this is a query interface on top of it
- Could use an LLM to parse the query into filters + a similarity anchor
- Would be the most demo-able feature by far

### Player projection system
Given a player's career arc to date, project performance for the next 1-3 seasons.

- Anchor to the aging curve: expected decline rate by age and position
- Regression-to-the-mean on rate stats (BABIP, strand rate, etc.)
- Confidence intervals widen with each projected year
- Pairs with the aging curve overlay — shows where the player *is* vs. where they're likely *going*
- Would be the most analytically ambitious feature in the tool

### Hall of Fame probability
Given a player's career trajectory at age X, what's the probability they reach Cooperstown?

- Requires a labeled training set (inducted vs. not)
- Logistic regression on career WAR, peak WAR, awards, longevity is a reasonable baseline
- Show as a career-stage progress indicator on the profile page

---

## Production Deployment

### Full production deployment with pipeline documentation
The tool currently runs locally. Getting it production-ready and documenting the data pipeline is itself a portfolio signal.

**What it takes:**
- Containerize backend + frontend (Docker Compose, or separate services)
- CI/CD pipeline: tests on PR, deploy on merge to main
- Environment config: secrets management, prod database, CORS settings
- Data pipeline docs in the repo: what data comes from where, ingest frequency, how to re-run from scratch

**Why it matters:** most portfolio projects are localhost demos. A live URL with a documented data pipeline shows you can operate a system end-to-end, not just build features. Baseball ops teams run actual pipelines — the ability to document and deploy one is a direct signal.

**Platform:** Render or Railway for the app (low-ops, free tier for hobby projects); Neon or Supabase for Postgres with a generous free tier.

---

## Scheduled Data Jobs

The DB needs periodic refreshes to stay current through a season. See [`SCHEDULED_JOBS.md`](SCHEDULED_JOBS.md) for the full breakdown.

**What needs scheduling:**
- Weekly stats refresh (BattingSeason, PitchingSeason, StatcastZoneBucket) — stats finalize ~3 days after games
- Season-start pass for new players and rookies not yet in the DB
- Post-season awards ingest (November)
- Similarity vector recompute after every stats update (vectors drift as the season progresses)

**Platform choice:** GitHub Actions cron is the lowest-friction option for a portfolio project (no extra infra, free tier, config lives in the repo). Django-Q or Celery Beat make more sense if the app needs real-time jobs or a retry queue.

**Three requirements for a trustworthy cron system:**
1. **Failure alerting** — a silent failure that leaves stale data is worse than no job at all
2. **Staleness detection** — the API should expose `last_updated` so stale data is visible in the UI
3. **Dependency ordering** — similarity vectors must recompute *after* the stats update completes, not in parallel

---

## Deferred / Won't Do Soon

- Platoon splits (vs LHP / RHP) — needs more granular data
- WPA / clutch stats — needs play-by-play data
- Export to PNG — nice-to-have, not core
- Mobile layout — currently desktop-only, not blocking for a portfolio tool

### xBA / xERA from first principles
Build own expected batting average and expected ERA models rather than consuming Baseball Savant's published numbers.

**Why from first principles:**
Baseball Savant already publishes xBA and xERA. The reason to build your own is not to get different numbers — it's to demonstrate you understand the machinery. xBA is essentially a logistic regression (or gradient boosted model) mapping launch angle + exit velocity → probability of hit, with adjustments for park and spray angle. xERA aggregates pitch-level expected outcomes into a rate stat. If you can only consume Savant's published values, you can't: (a) add features Savant doesn't expose (pitch location, count, batter handedness), (b) apply the methodology to contexts where Savant doesn't publish (minor leagues, historical pre-Statcast data), or (c) explain in an interview exactly how the number is constructed. Baseball ops teams build proprietary versions of these metrics precisely because the published ones are black boxes — building your own, even if it correlates closely with Savant's output, proves you can work inside the black box.

**Why deferred:** requires full pitch-level Statcast ingest (large dataset), and the output won't visually differ much from just displaying Savant's numbers. High methodological value, low demo value.

### WAR decomposition from first principles (own positional adjustments)
Reconstruct WAR from linear weights rather than using bWAR/fWAR directly, with documented positional adjustment decisions.

**Why from first principles:**
bWAR and fWAR regularly disagree by 1-3 WAR for the same player in the same season. The disagreement comes from different defensive metrics (DRS vs. UZR), different positional adjustments, different replacement-level baselines, and different park factor methodologies. Building your own WAR from components forces you to make each choice explicitly — what is the positional adjustment for a catcher vs. a corner outfielder, and why? Documenting where your version diverges from published WAR and explaining the reasoning is exactly the kind of analytical rigor R&D teams evaluate. Most applicants treat WAR as a given; being able to reconstruct it from components is a meaningful signal of depth.

The existing "WAR decomposition" entry in Priority 3 is about displaying bWAR's published component breakdown — this is different: computing the components yourself.

**Why deferred:** substantial modeling work with diminishing visual return. Better to cite the methodology gap clearly in interviews and have a scoped spec than to ship something that quietly disagrees with consensus WAR without a strong justification.
