# pca_v2

**Career Arc Visualizer** plots up to ten baseball careers side-by-side — WAR, OPS+, ERA+, and other metrics rendered as multi-line arcs with award glyphs at the seasons that matter. Toggle to an age-aligned axis to compare across eras (Ruth vs. Bonds, Koufax vs. Pedro); click a player card for a full profile with similar-player comps, a full season log, and Statcast pitch zones (2015+).

**Live at:** [pcav2-production.up.railway.app](https://pcav2-production.up.railway.app) · share state via URL — `/?compare=ruthba01,bondsba01` round-trips into the app.

**What's analytically interesting:** the similarity engine. Z-scored weighted distance over six role-specific features, with a two-axis position embedding (so catchers don't match with corner OFs) and saves-rate detection (Mariano clusters with Hoffman and Wagner, not starters at the same WAR). Pool-calibrated scores so the median candidate is always 30, era-adjusted metrics treated as first-class, and the full methodology in [`SIMILARITY.md`](SIMILARITY.md). Backed by ~150 years of season data from Baseball Reference plus Statcast pitch-level data from 2015+.

<!-- TODO: hero screenshot of compare chart -->

---

## Features

### Compare chart
Multi-player career arcs (up to 10 players). Metrics include WAR, HR, AVG, OPS, era-adjusted **OPS+** and **ERA+**, ERA, and SO. Calendar / by-age x-axis toggle for cross-era comparison. Brush range selector. URL is shareable — `/?compare=ruthba01,bondsba01` round-trips.

### Award glyphs
13 award types overlaid on the chart lines with priority resolution (e.g. Triple Crown beats MVP for the same year). Show/hide toggle. Hovering a season shows full award detail in the tooltip. Includes MVP, Cy Young, Gold Glove, Silver Slugger, World Series, Rookie of the Year, All-Star, All-MLB Team, Triple Crown (batting and pitching), Postseason MVP, batting title, and ERA title.

### Leaderboard
Career and peak stats for every qualifying player. Filterable by position (all 9 positions + DH + P), era preset, role; sortable by career WAR, peak WAR, HR, All-Star count. Award badges with hover tooltips.

### Player profiles
Hero block with bio (debut/final game derived from date fields, primary position with handedness for pitchers). Stat grid, sparkline panels, full season log, and:

- **Similar players panel** — top-4 batter and pitcher comps from a custom similarity engine (see below)
- **Awards panel** — chronological list of award wins
- **Pitch zone heatmap** — strike-zone hot/cold view for batting and pitching (Statcast, 2015+ only)

### Similarity engine (`players/similarity.py`)
Z-scored weighted Euclidean k-NN over a 6-feature vector per role:

- **Batters:** career WAR, peak WAR, OPS+, HR rate, position defensive value, position kind
- **Pitchers:** career WAR, peak WAR, ERA+, K/9, starter %, saves rate (closer detection)

Scores are pool-calibrated so the median candidate is always 30 — relative, not absolute. Two-axis position embedding keeps catchers from matching with corner outfielders. Saves-rate clusters Mariano Rivera with Hoffman/Wagner instead of starters with the same WAR. Full methodology in [`SIMILARITY.md`](SIMILARITY.md).

---

## Tech stack

**Backend:** Django 6 · Django REST Framework · django-filter · PostgreSQL 17 · pybaseball (Statcast pulls)

**Frontend:** React 18 · Vite · TypeScript · Visx (charts) · TanStack Query · React Router · Phosphor Icons

**Data sources:** Baseball Reference (season history, awards, fielding 1871–present), Lahman People.csv (birth dates), Baseball Savant via pybaseball (Statcast pitch-level 2015+).

---

## Setup

### Requirements
- Python 3.14+
- PostgreSQL 17+ with the [`pgvector`](https://github.com/pgvector/pgvector) extension (`brew install pgvector`) — required by migrations for the methodology RAG index
- Node.js 20+

### 1. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
createdb pca_v2
python manage.py migrate
```

Default DB connection assumes local Postgres with peer auth (Database `pca_v2`, User = your OS username, Host `localhost:5432`). Override in `pca_backend/settings.py` if needed.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev          # dev server on http://localhost:5173
```

The dev server proxies `/api` to the Django backend on `:8000`.

### 3. Run

```bash
# terminal 1
python manage.py runserver

# terminal 2
cd frontend && npm run dev
```

App runs at **http://localhost:5173**, API at **http://localhost:8000/api/**.

### AI features (optional)

The grounded career-narrative agent and methodology search work without any keys
— the narrative falls back to a deterministic template and search returns empty.
To enable the live LLM/RAG paths, set:

| Env var | Enables |
|---|---|
| `ANTHROPIC_API_KEY` | LLM-generated career narratives (`GET /api/players/{id}/narrative/`) |
| `VOYAGE_API_KEY` | Methodology embeddings + semantic search (run `index_methodology` after setting) |

`NARRATIVE_USE_TOOLS=false` switches the narrative from the tool-calling agent to a single-shot call.

---

## Data ingest

All scripts live in `pipeline/`. Each enforces a 10 req/min rate limit on Baseball Reference and logs completed pages to `IngestionLog` so re-runs are safe.

### Full season history (1871–present, ~30 min)
```bash
python pipeline/ingest_bref_history.py
```

Options: `--start-year`, `--end-year`, `--batting-only`, `--pitching-only`, `--dry-run`, `--force` (re-run completed pages).

After fielding ingest, `Player.primary_position` is recomputed automatically. To recompute manually:
```bash
python manage.py compute_primary_positions
```

### Awards
```bash
python pipeline/ingest_bref_awards.py
```

### Statcast pitch zones (2015+)
```bash
python pipeline/ingest_statcast_zones.py
```

### Methodology RAG index (for the narrative agent)
Embeds `frontend/src/methodology/*.md` into pgvector for semantic retrieval.
Requires `VOYAGE_API_KEY`:
```bash
python manage.py index_methodology
```

### Player bio backfill
Birth dates and debut/final game are populated from Lahman's People.csv:
```bash
python pipeline/backfill_player_bio.py
```

---

## API

Root: `http://localhost:8000/api/`

| Endpoint | Description |
|---|---|
| `GET /api/players/?search=ruth` | Player search by name or bbref_id |
| `GET /api/players/{bbref_id}/` | Player profile (bio, position, handedness) |
| `GET /api/players/{bbref_id}/batting/` | Career batting seasons |
| `GET /api/players/{bbref_id}/pitching/` | Career pitching seasons |
| `GET /api/players/{bbref_id}/awards/` | All awards for a player |
| `GET /api/players/{bbref_id}/similar/` | Top-4 batter and pitcher comps |
| `GET /api/players/{bbref_id}/zone/?role=B&outcome=hits` | Statcast pitch-zone bucket data |
| `GET /api/leaderboard/?position=CF&era=modern&ordering=-career_war` | Filterable career leaderboard |
| `GET /api/batting/?player={bbref_id}&year=1927` | Batting seasons with filters |
| `GET /api/pitching/?player={bbref_id}&ordering=-war` | Pitching seasons, sortable |

All list endpoints support `?ordering=<field>` and `?page=<n>` (50 rows/page).

---

## Tests

```bash
# backend ingest tests
python -m pytest pipeline/test_ingest.py -v

# frontend
cd frontend && npm test
```

Backend tests use a temporary database and rolled-back transactions — they do not touch your dev database.

### Narrative eval harness

Scores the narrative agent — hallucination rate (verifier-based), tool-selection
accuracy, and RAG hit-rate@k — over a fixed player/question sample:

```bash
python pipeline/eval_narrative.py                  # scorecard (degrades gracefully without keys)
python pipeline/eval_narrative.py --max-hallucination 0.0   # CI gate: exit 1 if any hallucination slips through
```

---

## Documentation

- [`ROADMAP.md`](ROADMAP.md) — full feature backlog, prioritized
- [`RELEASE_ROADMAP.md`](RELEASE_ROADMAP.md) — what ships when (resume / public release thresholds)
- [`SIMILARITY.md`](SIMILARITY.md) — similarity engine methodology
- [`AI_FEATURES.md`](AI_FEATURES.md) — grounded narrative agent: tool calls, RAG, evals, verification
- [`SCHEDULED_JOBS.md`](SCHEDULED_JOBS.md) — data refresh cron requirements
