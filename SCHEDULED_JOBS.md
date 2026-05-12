# Scheduled Jobs

Data refresh strategy for keeping the DB current through a live season.

---

## Update cadence by data type

| Data | Frequency | Notes |
|------|-----------|-------|
| `BattingSeason` / `PitchingSeason` | Weekly during season; once after offseason ends | Stats finalize ~3 days after each game. Running Monday covers the full prior week. |
| `StatcastZoneBucket` | Weekly during season | Zone buckets are pre-aggregated; re-aggregate from new Statcast rows after each stats update. |
| `PlayerAward` | Once per year (November) | Postseason awards (MVP, Cy Young, ROY, Gold Glove, Silver Slugger) announced in October–November. |
| Similarity vectors | After every stats update | Cosine similarity drifts as season progresses. Recompute only after stats are committed — not in parallel. |
| New players / rookies | Start of season + midseason callups | Players not yet in the DB need an initial ingest before any other job can reference them. |

---

## Dependency ordering

Jobs are not independent. Run them in this order:

```
1. Player bootstrap (new bbrefIds only)
2. BattingSeason + PitchingSeason refresh
3. StatcastZoneBucket re-aggregation
4. Similarity vector recompute
5. PlayerAward ingest (November only)
```

Running similarity vectors before stats complete will embed stale data and requires an immediate re-run. The job runner must enforce this sequence, not assume it.

---

## Platform options

### GitHub Actions cron (recommended for now)
- Zero extra infra — config lives in `.github/workflows/`
- Free tier covers weekly jobs comfortably
- Secrets (DB URL, API keys) go in repo secrets
- Failure notifications via email or Slack webhook on `on: failure`
- Limitation: no retry queue; a failed job requires a manual re-run or next scheduled firing

```yaml
# .github/workflows/refresh.yml
on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday 6am UTC
```

### Django-Q / Celery Beat
- Retry queues, priority lanes, per-task monitoring
- Required if jobs grow beyond a single script (e.g., fan-out per player)
- Adds Redis/broker dependency — overkill for a portfolio project until the job count justifies it

### Railway / Render built-in cron
- Point-and-click cron that shells into the running service
- Good middle ground: no broker, but visible in the platform dashboard
- Logs are retained per-run, easier to audit than GitHub Actions artifacts

---

## Request volume estimates

| Job | Requests per run | Source |
|-----|-----------------|--------|
| Initial full ingest (one-time) | ~10,000–30,000 | pybaseball / Baseball Reference |
| Weekly stats refresh (season) | ~500–2,000 | New games since last run |
| StatcastZone re-aggregation | ~200–500 | Statcast per-pitch rows |
| Awards ingest | < 100 | Once per year |

---

## Risks and mitigations

### ToS and rate limiting
pybaseball scrapes Baseball Reference and Baseball Savant. Neither has a public API — Sports Reference [explicitly states](https://www.sports-reference.com/bot-traffic.html) they cannot offer one due to third-party data licensing agreements.

**Actual rate limit (as of May 2024):**
- Baseball Reference: **20 requests per minute**
- FBref / Stathead: **10 requests per minute**
- Violation consequence: session jailed for **up to 24 hours** — applies to any bot regardless of how it's constructed

**What this means for job timing:**

| Job | Request count | Min wall time at 20 req/min |
|-----|--------------|----------------------------|
| Initial full ingest (one-time) | ~10,000–30,000 | 8–25 hours |
| Weekly stats refresh | ~500–2,000 | 25–100 minutes |
| StatcastZone re-aggregation | ~200–500 | 10–25 minutes |

The initial ingest must run unattended overnight. Weekly jobs fit comfortably in an hour if paced correctly.

**Mitigations:**
- `time.sleep(3.5)` between requests gives ~17 req/min — comfortably under the 20/min ceiling
- pybaseball exposes a `wait` param — set it and don't override it
- Cache raw responses locally so a mid-run failure doesn't require re-fetching already-retrieved pages
- Run during off-peak hours (early morning UTC); the rate limit is per-session, not per-IP, but polite timing reduces server load
- Do **not** attempt to route around the limit via proxies — Sports Reference's ToS prohibits it and risks a permanent block

### API instability
pybaseball is a third-party scraper. If Baseball Reference changes their HTML structure, pybaseball breaks silently — returning empty DataFrames or raising parse errors.

**Mitigation:** validate row counts after each fetch. If a player who had 15 seasons returns 0 rows, treat it as a failure, not an update.

### Partial run consistency
A job that updates 3,000 players but crashes at player 1,400 leaves the DB in a mixed state: some players have 2026 data, others don't.

**Mitigation:** use an `IngestionLog` table (or equivalent) to track the last successful ingest timestamp per player. On failure, the next run resumes from the first un-updated player rather than restarting from scratch.

### Memory
pybaseball loads full season tables into pandas DataFrames before filtering. For a large player list this can spike memory. Process players in batches of 100–200 rather than loading everything at once.

---

## Three requirements for a trustworthy cron system

1. **Failure alerting** — a silent failure that leaves data stale is worse than no job. Every run must emit a success/failure signal to a channel someone watches (email, Slack, PagerDuty).

2. **Staleness detection** — the API should expose a `last_updated` timestamp on responses so stale data is visible in the UI. Users should know if the data is 3 days old vs. 3 months old.

3. **Dependency ordering** — similarity vectors must recompute *after* stats complete. The job runner (Actions, Django-Q, whatever) must enforce this ordering, not rely on approximate timing.
