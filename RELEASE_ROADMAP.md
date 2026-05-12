# Release Roadmap

Two thresholds, two scopes. The general feature backlog lives in [`ROADMAP.md`](ROADMAP.md). This doc is just "what ships when."

---

## Threshold 1 — Resume / first deployment

Goal: a live URL that holds up to a 60-second skim by a baseball ops recruiter or a generalist SWE recruiter.

A live URL is the single thing that separates "weekend project" from "operates a system." Most CS resumes don't have one. Don't ship more features before deploying.

### Must-ship

- [ ] **Production deployment**
  Render or Railway for the app + Neon or Supabase for Postgres. Containerize backend + frontend, basic CI/CD, environment config / secrets.
- [ ] **HOF Monitor + Black Ink + Gray Ink**
  One signature analytical feature on the profile page next to career WAR. James scores are the highest credibility per hour of work — pure SQL aggregations, intellectually credible, read as serious sabermetrics.
- [ ] **Era-adjusted toggle on the compare chart**
  OPS+ and ERA+ are already in the DB — just surface them as a toggle. The "Babe Ruth's .342 BA vs. Tony Gwynn's .338" question is the first thing a baseball person will think; not having an answer is a tell.
- [ ] **README cleanup**
  Current README still says comparison charts are "in progress" and doesn't mention the leaderboard, similarity, awards, or any of the analytical work. Should match what the live app actually does — link to it, screenshot it, name the analytical features.
- [ ] **Scheduled jobs MVP (or staleness disclosure)**
  If you deploy and data is from May 2026 forever, that's worse than not deploying. Either wire up a weekly GitHub Actions cron (see [`SCHEDULED_JOBS.md`](SCHEDULED_JOBS.md)) or surface a "last updated" date in the UI so the staleness is honest.

Realistic scope: ~1–2 weeks.

---

## Threshold 2 — Public release / r/sabermetrics, Tangotiger spaces

Goal: holds up to scrutiny from people who actually know baseball analytics. This audience will click the similarity panel and ask "why is Ruth similar to Pujols?" They'll notice missing eras. They'll diff your numbers against bWAR.

Everything above is a prerequisite. Then:

### Must-ship

- [ ] **Methodology documentation page**
  The single most important addition. Document the similarity weights (the numbers in `players/similarity.py` are nontrivial choices), the era cutoffs, what counts as "qualified," and where your numbers diverge from bWAR / fWAR. This audience won't mind your version of WAR — they'll mind not knowing it's your version. A simple `/about` page or markdown doc linked from the footer.
- [ ] **Aging curve overlay**
  The canonical "real analytics tool" feature. Anyone evaluating a player thinks about aging implicitly; surfacing it makes the tool feel professional. Natural pair to the age/calendar toggle already shipped.
- [ ] **Percentile rankings**
  When this audience looks at a stat, the first instinct is to rank it. "12th all-time among CF by career WAR" answers the question they were already asking. Now that `primary_position` exists, by-position percentiles become possible.
- [ ] **Missing-data honesty**
  Pitch zones only work for 2015+. Older players have no Statcast. Currently this likely shows an empty panel. Should say "no Statcast data before 2015" explicitly. Same for any other coverage gap.
- [ ] **Performance pass**
  Page-load timing, prefetch on hover for leaderboard rows, no skeleton flicker on the compare chart, no jank when switching metrics. This community is impatient — a slow tool gets closed before the analytical depth lands.

Realistic scope: ~2–3 weeks on top of threshold 1.

---

## Explicit non-goals for both thresholds

Skip these for now, even though they sit in [`ROADMAP.md`](ROADMAP.md):

- **Stuff+ implementation** — multi-week Statcast modeling, low visual return for the cost
- **Pitch arsenal analysis** — same
- **Player projection system** — same
- **Hall of Fame probability model** — same
- **Natural language player search** — fun but a distraction from the analytical core
- **xBA / xERA from first principles** — already deferred in `ROADMAP.md`
- **WAR decomposition from first principles** — already deferred in `ROADMAP.md`
- **Mobile layout** — desktop-only is fine for both thresholds; a "see desktop" warning is sufficient

The honest framing for both audiences is **"compact, well-scoped tool with documented methodology."** That beats "ambitious tool with unverified numbers" with this crowd specifically.
