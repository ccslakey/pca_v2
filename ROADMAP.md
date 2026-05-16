# Roadmap

Living doc covering current status, what's next, the launch playbook, and the longer feature backlog. Update as priorities shift or features ship.

Live at: https://pcav2-production.up.railway.app

---

## Now — finish before public launch

Blocks Threshold 2 (release post on r/sabermetrics, Tangotiger circles, etc.). Threshold 1 — "live URL that holds up to a 60-second skim" — shipped. Most of the original Threshold 2 list (methodology page, missing-data honesty, aging curve, percentile rankings, performance pass, CI, scheduled jobs) is done — see `Shipped`. What's left is observability, mobile, and the items that make the launch *spread*.

### Must-ship

- [ ] **Analytics** — Plausible or Umami (not GA). Without page-view + popular-comparison telemetry, every post-launch decision is vibes. ~30 min setup. Ship before the 5-person wave.
- [ ] **Error monitoring** — Sentry free tier. At 50+ users tailing logs stops working. Ship before the 20-person wave.
- [ ] **Mobile layout** — previously deferred, but the friends-and-family wave will open links on phones. Minimum: usable single-column profile + compare page that doesn't break. Sabermetric audience still expected on desktop, so the bar is "doesn't embarrass," not "feature parity."
- [ ] **OG images** — see [Social preview images](#social-preview-images-open-graph) below. Not for virality — for the case when *you* post a comparison to Twitter / Bluesky / LinkedIn during the hiring push. Preview being a real chart vs. a generic card is what makes a hiring manager click. Cache rendered PNGs hard; rate-limit the endpoint.
- [ ] **Engineering write-up** — short post (blog, expanded README section, or LinkedIn) walking through the similarity engine, era adjustments, and methodology tradeoffs. Sabermetric-leaning hiring managers absorb depth from prose much faster than by clicking around a UI; this is probably the single highest-leverage *hiring* signal you can add beyond what's already shipped. (SEO is deferred — see Distribution playbook — since this project is for hiring, not anonymous Google traffic.)
- [ ] **Career rate-stat slash line in the hero** — career AVG/OBP/SLG/OPS (or ERA/WHIP/K9 for pitchers) computed from existing totals. People expect this on a player page; absence reads as incomplete.
- [ ] **Team timeline on the profile** — horizontal stripe showing which teams the player played for and when, derived from the `team` field on season tables. Visual richness for almost no work.
- [ ] **Career milestone overlay** — mark the season a player crossed 500 HR / 3000 H / 300 W / 3000 K / 2000 RBI as labeled markers on the career arc. Good demo material; "the season Bonds passed Ruth" is a shareable screenshot.

---

## Distribution playbook (when ready to launch)

Don't post until the methodology page is live. This audience converts on *evidence of analytical rigor*; lead with that.

### Coordinated launch — one day, multiple channels

- r/sabermetrics
- r/baseball
- Show HN ("Show HN: cross-era baseball comparison tool with documented methodology")
- Tangotiger blog comments (he reads every one)
- Bluesky baseball-analytics circles
- SABR mailing list / forum

One coordinated launch outperforms six tweets over two months.

### Social preview images (Open Graph)

When `/?compare=ruthba01,bondsba01` gets shared on Twitter / Bluesky / Discord, the preview should show the actual chart, not a generic OG card. Highest-leverage thing for organic spread; one well-shared comparison pulls in hundreds of users.

Approach: `/api/og/?compare=...` endpoint that renders the chart server-side (matplotlib or Playwright headless), returns 1200×630 PNG. Page-level `<meta property="og:image">` points to it.

### SEO for player name searches

People Google "Mike Trout career stats" constantly. Player profile pages ranking = free evergreen traffic.

- `sitemap.xml` covering all ~24k player URLs
- Per-page `<meta description>` ("Mike Trout career WAR, OPS+, similar players, era-adjusted stats")
- JSON-LD `Person` schema (BBref does this — gets you in Google Knowledge Panel range)
- Lighthouse > 90 (page speed is a ranking signal)

Data is already there. Pure surfacing work.

---

## Feature backlog

Not scheduled. Pulled into "Now" when the slot opens.

### Fast analytical wins (uses existing data, no new ingest)

- **League leadership badges** — for each season in the season-log panel, small "1st" / "T-2nd" badges next to WAR, HR, ERA, etc. when the player led/co-led the league.
- **`AnnotationGlyph` variants** — add ws, ss, hof, roty, tc, postmvp, bat_title, era_title, all_mlb variants.

### Analytical depth (resume differentiators)

- **"Similar through age N"** — extend the similarity engine to support comps at any career stage, not just career totals. Canonical prospect-comp question. See [`SIMILARITY.md`](SIMILARITY.md).
- **Stuff+** — pitch-quality metric measuring expected whiffs and weak contact, holding location constant. Requires Statcast pitch-level data; regress whiff rate on pitch characteristics within pitch-type buckets.
- **Pitch arsenal analysis** — usage rates by count/platoon/leverage, movement profile plots, tunnel analysis.
- **WAR decomposition (data ingest)** — break career WAR into batting / fielding / baserunning / positional components on the profile page. BBref exposes these.

### Ambitious / differentiating

- **Natural language player search** — "pitchers like Sandy Koufax but modern era." Similarity embedding model exists; this is a query interface on top of it. LLM parses query into filters + similarity anchor.
- **Player projection system** — given career arc to date, project 1–3 seasons. Anchors to aging curve + regression to mean on rate stats. Confidence intervals widen each year.
- **Hall of Fame probability** — given career trajectory at age X, probability of Cooperstown. Logistic regression on career WAR / peak / awards / longevity as baseline.

### Infrastructure

- **Redis cache for `similar/` aggregations** — currently uses Django's `LocMemCache` (1h TTL, per-process). Only worth upgrading if running multiple Gunicorn workers; running single worker for now. Add explicit cache invalidation at end of ingest scripts.

---

## Won't do soon / deferred

- **Newsletter / weekly content** — that's a job, not a portfolio feature
- **Accounts / login** — kills bounce, adds DB schema, adds spam vector
- **AI features ("explain this player")** — dilutes the methodology positioning that is the actual edge with this audience
- **Notifications / email captures** — friction without proportional value
- **Comments / community features** — moderation cost, low signal
- **Platoon splits (vs LHP/RHP)** — needs more granular data
- **WPA / clutch stats** — needs play-by-play data
- **Export to PNG** — nice-to-have, not core
- **xBA / xERA from first principles** — high methodological value, low demo value; output won't visually differ from Savant's. Better to explain the gap in interviews.
- **WAR decomposition from first principles** — bWAR/fWAR regularly disagree by 1–3 WAR; building your own forces each choice to be explicit. Substantial modeling work, diminishing visual return.

---

## Shipped

### Production
- Live deployment to Railway (Postgres + Dockerfile + WhiteNoise SPA serve + healthcheck)
- Env-driven Django settings
- 215 MB production database (full local dataset including Statcast zones)
- Methodology page documenting similarity weights, era cutoffs, qualification thresholds, and where numbers diverge from bWAR/fWAR (linked from footer)
- Scheduled data jobs: weekly stats refresh + season-start + post-season awards + similarity recompute, with failure alerting, staleness detection (`/api/meta/`), and dependency ordering (similarity after stats) — see [`SCHEDULED_JOBS.md`](SCHEDULED_JOBS.md)

### Analytical features
- Positional percentile rankings: career WAR vs same-position pool, shown on profile stat grid and compare cards with rank-on-hover tooltip
- Aging curve overlay: positional average by age on compare chart, all metrics, solid/faded confidence tiers
- Bug fix: NL pitcher strikeout totals (Pedro Martinez, Cy Young, etc.) were silently replaced by batting SO due to hr===null guard in mergeSeasons
- Bill James scores: HOF Monitor + Black Ink + Gray Ink, surfaced on profile page
- Era-adjusted toggle on compare chart (OPS+, ERA+)
- Similarity engine: multi-dimensional weighted distance with two-way player split, exponential-decay score, role/position embeddings, calibrated similarity scores
- Pitch zone heatmap (StatcastZoneBucket model + 20×20 grid SVG with role tabs)
- Awards data model (14 kinds), API action, profile panel, glyphs on the compare chart with priority system

### Compare page
- Shareable multi-player URLs (`?compare=...`)
- Award glyphs on chart lines, show/hide toggle
- Age / Calendar X-axis toggle
- FeaturedGallery: horizontal scroll of 14 curated comparison trios; auto-picks a random trio on first load
- Skeleton loading states (chart + player cards)

### Profile page
- Hero, stat grid, sparkline grid, season table, similar players panel, awards panel, pitch zone panel
- ProfilePageSkeleton for full-page loading state
- Staleness disclosure footer
- Missing-data honesty: explicit "no Statcast data before 2015" treatment on pitch-zone panel and any other coverage-gapped panels (no more empty silent panels)

### Browse / discovery
- Leaderboard page: position, era, WAR filters; sortable; award badge tooltips

### Data
- Player bio dates as DateField (birth/debut/final_game) end-to-end
- Player position data (FieldingSeason model, primary_position, ingest, filtering)
- Awards ingestion
- Statcast zone bucket ingestion
- Incremental Statcast ingest

### Engineering
- Data ingestion pipeline with retry/backoff, idempotency, 53 tests
- Django REST API with filtering and pagination
- React + TypeScript frontend (Vite, React Router, TanStack Query)
- Visx chart conversion (CareerChart, BrushChart, ProfileChart, Sparkline)
- API tests (APIClient) + frontend tests (component + hook coverage)
- Code quality refactor: glyph redesign, ProfilePage split into panels, CSS modularization (SCSS)
- Cached similarity aggregation queries (LocMemCache, 1h)
- README cleanup matching live app
- GitHub Actions CI: lint + `pytest` + frontend build on push
- Performance pass: page-load timing, prefetch on hover for leaderboard rows, no skeleton flicker, no jank when switching metrics

---

## Known integrity issues

### Monthly heatmap (cut)
Removed because previous version generated fake data from a seeded RNG — credibility hit in a data tool. Real options:
- Ingest monthly splits from Baseball Reference or Statcast (Statcast has month-level for 2015+)
- Until then: panel stays removed
