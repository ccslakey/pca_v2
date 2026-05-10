# Tasks

Portfolio improvement backlog — ordered by priority.

## Up next

- [ ] GitHub Actions CI — lint + `pytest` + frontend build on push
- [ ] Code quality
  - [ ] Extract `similar` view logic to `players/similarity.py`
  - [ ] Remove unused `rank` variable in similarity loop
  - [ ] Remove dead `color` prop from `PitchZone` (or wire to strike zone stroke)
  - [ ] Split `ProfilePage.tsx` (448 lines) into panel components
  - [ ] Split `globals.css` (651 lines) by concern
  - [ ] Redo `AnnotationGlyph` — add variants for ws, ss, hof, roty, tc, postmvp, bat_title, era_title, all_mlb

## Backlog

- [ ] Env var configuration — replace hardcoded `settings.py` values with `python-decouple` or `django-environ`
- [ ] Docker — `Dockerfile` + `docker-compose.yml` for local parity and deploy readiness
- [ ] Live deployment — Railway or Fly.io; blocked on Docker + env vars
- [ ] Cache `similar/` aggregation queries with Redis — currently uses Django's `LocMemCache` (1 h TTL, per-process); switch to Redis for cross-process sharing and add explicit invalidation in ingest scripts when seasons are written
- [ ] Remove or replace fake monthly heatmap data — real source is `pybaseball.get_splits` but costs 1 BRef req/player/year (see `pipeline/explore_monthly_splits.py`); shelved

## Done

- [x] Data ingestion pipeline — BRef scraper, retry/backoff, idempotency, 53 tests
- [x] Django REST API — `PlayerViewSet`, `BattingSeasonViewSet`, `PitchingSeasonViewSet`, filtering, pagination
- [x] Awards data model (`PlayerAward`, 14 kinds), ingest script, `awards/` API action, frontend hook + ProfilePage panel
- [x] Pitch zone heatmap — `StatcastZoneBucket` model, `ingest_statcast_zones.py`, `pitch_zone/` API action, `PitchZone` SVG component (20×20 grid, 5-layer blur, role tabs for two-way players)
- [x] `similar/` endpoint — multi-dimensional weighted distance (WAR, peak WAR, OPS+, ERA+, K/9, SP%); two-way player split; exponential-decay similarity score; 1 h aggregate cache
- [x] React + TypeScript frontend — Vite, React Router, TanStack Query
- [x] Visx chart conversion — `CareerChart`, `BrushChart`, `ProfileChart`, `Sparkline`
- [x] Player profile page — hero, stat grid, sparkline grid, season table, similar players panel, awards panel, pitch zone panel
- [x] `?compare=` URL seeding on compare page
- [x] `playerColor` / `colorTint` shared utilities
- [x] API tests — viewset coverage with `APIClient`
- [x] Frontend tests — component and hook coverage
