# Analytics

Product analytics run on PostHog; errors go to Sentry. Both are off unless their keys are set, so dev and tests never report.

## Privacy model

There are no accounts, so the goal is to never collect anything that could identify a person.

- **Cookieless mode.** PostHog derives a daily-rotating hash from IP + user agent server-side; nothing is stored on the device, so no consent banner is needed. The trade-off: no cross-day retention, and weekly/monthly uniques are overcounted.
- **No person profiles, no `identify()`, no autocapture, no session replay.**
- **URLs** keep only allowlisted query params (`compare`, `utm_*`, and structured leaderboard/zone params). Free-text `search`/`q` and anything appended by third parties (email trackers, `fbclid`, `gclid`) are dropped. Referrers are reduced to their origin. See `frontend/src/observability.ts` and `pca_backend/observability.py` — the allowlist lives in both.
- **Server events** use a fixed `distinct_id` (`pca-backend`) and never include prompt or output text.
- **Project settings** (PostHog): *Discard client IP data* on, *Cookieless server hash mode* on. (Sentry): *Prevent storing of IP addresses* on.

## Configuration

| Variable | Where | Purpose |
|---|---|---|
| `VITE_POSTHOG_KEY` | Railway (build arg) | PostHog project key for the browser |
| `VITE_POSTHOG_HOST` | Railway (build arg) | Optional; defaults to `https://us.i.posthog.com` |
| `POSTHOG_API_KEY` | Railway (runtime) | Same project key, for server events |
| `POSTHOG_HOST` | Railway (runtime) | Optional; same default |
| `VITE_SENTRY_DSN` / `SENTRY_DSN` | Railway | Sentry DSN for browser / Django |

## Events

Automatic: `$pageview` (initial load and on path change) and `$pageleave`.

All client events carry `surface` (`desktop` / `mobile`, or the leaderboard's host page) unless noted.

| Event | Properties | Fires from |
|---|---|---|
| `compare_player_added` | `player_id`, `player_count`, `source` (`search` / `browser`) | `ComparePage`, `MobileCompare` |
| `compare_player_removed` | `player_id`, `player_count` | `ComparePage`, `MobileCompare` |
| `featured_comparison_selected` | `player_ids` | `ComparePage` (featured gallery click; the auto-picked trio on first load is not tracked) |
| `chart_metric_changed` | `metric`, `page` (`compare` / `profile`) | `ComparePage`, `ProfilePage`, `MobileCompare`, `MobileProfile` |
| `compare_axis_changed` | `x_mode` (`year` / `age`) | `ComparePage` (no `surface`; desktop only) |
| `award_glyphs_toggled` | `visible` | `ComparePage` (no `surface`; desktop only) |
| `similar_player_clicked` | `from_player_id`, `to_player_id`, `similarity`, `rank` | `SimilarPlayersPanel`, `MobileProfile` |
| `leaderboard_filtered` | `filter` (`pos` / `era` / `min_war`), `value` | `PlayerBrowser`, `MobileLeaders` |
| `leaderboard_sorted` | `sort`, `order` | `PlayerBrowser`, `MobileLeaders` |
| `narrative_trace_expanded` | `player_id` | `NarrativePanel` (no `surface`) |
| `player_saved_toggled` | `player_id`, `saved` | `MobileProfile` (no `surface`) |
| `narrative_served` *(server)* | `player_id`, `cached`, `source` (`llm` / `template`); when not cached also `model`, `mode`, `latency_ms`, `model_calls`, `tool_calls`, `repairs`, `flagged_count`, `input_tokens`, `output_tokens`, `cache_read_tokens` | `players/narrative.py` `get_or_generate` |

## Adding an event

Call `track('object_verb', {...})` from `frontend/src/analytics.ts` (or `analytics.capture` on the server), use snake_case `object_verb` names, keep properties to IDs, enums, counts and flags (never free text), and add a row above.
