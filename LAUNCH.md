# Launch & Engagement

How to get people to find this thing, try it, and come back. Ranked by ROI for a portfolio project — not a SaaS business.

---

## 1. Don't land on an empty state

First visit should already be analytical. A default comparison pre-loaded, or a homepage gallery above the chart with curated matchups ("Power hitters by era", "Aces of the dead-ball era", "Closers"). Empty chart → bounce.

Pair this with skeleton states for any panel that depends on a fetch — never show users a blank or jumping layout while data loads.

---

## 2. Social preview images (Open Graph)

When `/?compare=ruthba01,bondsba01` is shared on Twitter / Discord / Bluesky, the preview should show the actual chart — not a generic OG card. Server-side PNG generation per URL is real engineering work, but one well-shared comparison pulls in hundreds of users. Highest-leverage thing for organic spread.

Approach: a `/api/og/?compare=...` endpoint that renders the chart server-side (matplotlib or Playwright headless) and returns a 1200×630 PNG. Page-level `<meta property="og:image">` points to it. Twitter, Bluesky, Discord, Slack all unfurl it.

---

## 3. SEO for player name searches

People Google "Mike Trout career stats" constantly. If your player profile pages rank, that's free evergreen traffic. Need:

- `sitemap.xml` covering all ~20k player URLs
- Per-page `<meta description>` ("Mike Trout career WAR, OPS+, similar players, era-adjusted stats")
- JSON-LD `Person` schema (BBref does this — gets you in Google Knowledge Panel range)
- Lighthouse score > 90 (page speed is a ranking signal)

Data structure is already there. Pure surfacing work.

---

## 4. One coordinated launch, not a slow drip

Pick a day. Post simultaneously to:

- r/sabermetrics
- r/baseball
- Show HN ("Show HN: cross-era baseball comparison tool with documented methodology")
- Tangotiger blog comments (he reads every one)
- Bluesky baseball analytics circles
- SABR mailing list / forum

Lead with the methodology page, not the visual polish. This audience respects "here's where I diverge from bWAR" far more than UI work. One coordinated launch outperforms six tweets over two months.

---

## 5. Curated comparison gallery

A "Featured matchups" section with 10–20 hand-picked comparisons. Each is a permanent linkable URL with a story. Doubles as:

- SEO landing pages ("Mariano Rivera vs Trevor Hoffman")
- Seeds for social shares
- Entry points for users who don't know what to type

Pick the ones that tell a story: dead-ball aces, post-war power, the 2001 Bonds discussion, modern catchers, the closer revolution.

---

## What to skip

- **Newsletter / weekly content** — that's a job, not a portfolio feature
- **Accounts / login** — kills bounce rates, adds DB schema, adds spam vector
- **AI features** ("explain this player") — dilutes the methodology positioning that is the actual edge with this audience
- **Notifications / email captures** — friction without proportional value
- **Comments / community features** — moderation cost, low signal

The mental model: this audience converts on *evidence of analytical rigor*. Make `SIMILARITY.md` (and a future `METHODOLOGY.md`) prominent and link to them everywhere. Let the analytical content do the persuading; the tool sells itself once they land.
