# Tasks

Portfolio improvement backlog — ordered by priority.

## In progress

- [ ] API tests — viewset coverage with `APIClient`
- [ ] Frontend tests — component and hook coverage

## Up next

- [ ] GitHub Actions CI — lint + `pytest` + frontend build on push

## Backlog

- [ ] Env var configuration — replace hardcoded `settings.py` values with `python-decouple` or `django-environ`
- [ ] Docker — `Dockerfile` + `docker-compose.yml` for local parity and deploy readiness
- [ ] Live deployment — Railway or Fly.io; blocked on Docker + env vars
- [ ] Remove or implement awards section — currently a dead placeholder in `ProfilePage`
- [ ] Remove or replace fake monthly heatmap data — currently synthetic RNG; needs real monthly split data or should be cut
- [ ] Improve similarity algorithm — era-adjusted WAR, peak vs longevity weighting, finer position breakdown

## Done

- [x] Data ingestion pipeline — BRef scraper, retry/backoff, idempotency, 53 tests
- [x] Django REST API — `PlayerViewSet`, `BattingSeasonViewSet`, `PitchingSeasonViewSet`, filtering, pagination
- [x] `similar/` endpoint — WAR-based similarity with bulk aggregation
- [x] React + TypeScript frontend — Vite, React Router, TanStack Query
- [x] Visx chart conversion — `CareerChart`, `BrushChart`, `ProfileChart`, `Sparkline`
- [x] Player profile page — hero, stat grid, sparkline grid, season table, similar players panel
- [x] Monthly heatmap component
- [x] `?compare=` URL seeding on compare page
- [x] `playerColor` / `colorTint` shared utilities
