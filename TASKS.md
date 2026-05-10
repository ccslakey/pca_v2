# Tasks

Portfolio improvement backlog — ordered by priority.

## In progress

- [x] API tests — viewset coverage with `APIClient`
- [x] Frontend tests — component and hook coverage

## Up next

- [ ] GitHub Actions CI — lint + `pytest` + frontend build on push

## Backlog

- [ ] Env var configuration — replace hardcoded `settings.py` values with `python-decouple` or `django-environ`
- [ ] Docker — `Dockerfile` + `docker-compose.yml` for local parity and deploy readiness
- [ ] Live deployment — Railway or Fly.io; blocked on Docker + env vars
- [ ] New `AnnotationGlyph` variants for new kind values (ws, ss, hof, etc.); ProfileChart annotation overlay

---

### Execution order

1. Migration (model + Player fields)
2. `pipeline/ingest_bref_awards.py` (dry-run mode, idempotent via `IngestionLog`)
3. Tests for the ingest script
4. API endpoint
5. Frontend


- [ ] Remove or replace fake monthly heatmap data — real source is `pybaseball.get_splits` but costs 1 BRef req/player/year (see `pipeline/explore_monthly_splits.py`); options are on-demand cache or WAR-threshold ingest; shelved
- [ ] Improve similarity algorithm — era-adjusted WAR, peak vs longevity weighting, finer position breakdown

## Done

- [x] Data ingestion pipeline — BRef scraper, retry/backoff, idempotency, 53 tests
- [x] Django REST API — `PlayerViewSet`, `BattingSeasonViewSet`, `PitchingSeasonViewSet`, filtering, pagination
- [x] `similar/` endpoint — WAR-based similarity with bulk aggregation
- [x] Awards data model (`PlayerAward`, 14 kinds), ingest script (`pipeline/ingest_bref_awards.py`), `awards/` API action, frontend hook + ProfilePage panel
- [x] React + TypeScript frontend — Vite, React Router, TanStack Query
- [x] Visx chart conversion — `CareerChart`, `BrushChart`, `ProfileChart`, `Sparkline`
- [x] Player profile page — hero, stat grid, sparkline grid, season table, similar players panel
- [x] Monthly heatmap component
- [x] `?compare=` URL seeding on compare page
- [x] `playerColor` / `colorTint` shared utilities
