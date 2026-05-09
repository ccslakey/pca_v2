# pca_v2

Baseball analytics app. Django REST API backed by a PostgreSQL database populated from Baseball Reference (1871–present). React + Vite frontend with player comparison charts (in progress).

## Requirements

- Python 3.14+
- PostgreSQL 17+

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv env
source env/bin/activate
```

### 2. Install dependencies

```bash
pip install django==6.0.5 djangorestframework==3.17.1 django-filter==25.2 \
    django-cors-headers==4.9.0 psycopg2-binary==2.9.12 \
    pybaseball==2.2.7 beautifulsoup4 lxml \
    pytest==9.0.3 pytest-django==4.12.0
```

### 3. Create the database

```bash
createdb pca_v2
```

The default settings expect a local PostgreSQL instance with:
- Database: `pca_v2`
- User: your OS username (peer auth, no password)
- Host: `localhost`, Port: `5432`

If your setup differs, edit `pca_backend/settings.py` → `DATABASES`.

### 4. Run migrations

```bash
python manage.py migrate
```

## Running the API server

```bash
python manage.py runserver
```

API root is at `http://localhost:8000/api/`.

### Key endpoints

| Endpoint | Description |
|---|---|
| `GET /api/players/?search=ruth` | Player search (name or bbref_id) |
| `GET /api/players/{bbref_id}/` | Player profile |
| `GET /api/players/{bbref_id}/batting/` | Career batting seasons |
| `GET /api/players/{bbref_id}/pitching/` | Career pitching seasons |
| `GET /api/batting/?player={bbref_id}&year=1927` | Batting seasons with filters |
| `GET /api/pitching/?player={bbref_id}&ordering=-war` | Pitching seasons, sortable |

All list endpoints support `?ordering=<field>` and `?page=<n>` (50 rows/page).

## Ingesting data from Baseball Reference

The pipeline scrapes BRef standard batting and pitching pages for every season in MLB history. It enforces a 10 req/min rate limit and logs each completed page so re-runs are safe.

**Full history (1871–present, ~30 min):**
```bash
python pipeline/ingest_bref_history.py
```

**Options:**
```bash
# Specific year range
python pipeline/ingest_bref_history.py --start-year 1990 --end-year 2024

# Batting or pitching only
python pipeline/ingest_bref_history.py --batting-only
python pipeline/ingest_bref_history.py --pitching-only

# Preview without writing to the database
python pipeline/ingest_bref_history.py --dry-run

# Re-ingest years already marked as complete
python pipeline/ingest_bref_history.py --force
```

Completed pages are recorded in the `IngestionLog` table. Failed pages are logged with `status='error'` and can be retried with `--force --start-year X --end-year X`.

## Running tests

```bash
python -m pytest pipeline/test_ingest.py -v
```

Tests use a temporary database created and destroyed per run — they do not touch the production database. Each test runs inside a rolled-back transaction.

To run a specific test class:
```bash
python -m pytest pipeline/test_ingest.py::TestIngestBattingPage -v
```
