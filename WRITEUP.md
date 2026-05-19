# Building a Cross-Era Baseball Comparison Tool

Comparing players across eras is one of the oldest arguments in baseball. It predates the box score. Could Babe Ruth play in today's league? Would Ohtani go yard in the dead-ball era? What kinds of players had a career similar to Greg Maddux's? The obvious move is to compare stats, but raw stats lie across eras, and even adjusted stats don't capture the shape of a career. This project is an attempt to do it properly.

---

## Why raw stats don't work

The game has changed enormously over its history. The dead-ball era. The pitching-dominant 60s. The offensive explosion of the 90s. The strikeout-heavy modern game. Rule changes, league expansion, integration, modern training and recovery. A home run in 1915 and a home run in 1999 are not the same event. Raw stats lie when you compare across eras, and that's before you get to the next problem below.

Even era-adjusted stats don't capture the shape of a career. Two players can finish with the same career WAR and have nothing in common: one a steady accumulator over twenty seasons, the other a five-year supernova who hung on for a decade. When you compare players, what you actually want to know is the arc: when they peaked, how long the peak lasted, what kind of decline they had. That's what this project tries to capture.

---

## The similarity engine

The core of the tool is a multi-dimensional weighted distance function. For any two players, it computes a similarity score based on a set of career metrics, each weighted according to how much that metric actually differentiates players. The result is a score, not a ranking, calibrated so that "90% similar" means something consistent regardless of who you're comparing.

The hard part isn't the math. The hard part is deciding what to include and how much to weight each dimension.

WAR gets the most weight. It's the only stat that captures total value in a single number, combining batting, fielding, baserunning, and positional adjustment. It's imperfect, it's the subject of ongoing methodological debate, and it's still the best single measure we have.

Rate stats are included alongside counting stats. A player who put up a .950 OPS over eight seasons is not the same as one who put up a .800 OPS over fifteen, even if their career totals overlap. Both dimensions matter and they tell different stories.

Position is handled through role embeddings rather than a strict positional filter. Comparing a shortstop to a second baseman is reasonable. Comparing an infielder to a starting pitcher is not. The engine respects that boundary without forcing rigid position-by-position silos.

The similarity computation is two-way. Player A's similarity to Player B is calculated separately from Player B's similarity to Player A, then averaged. This matters because asymmetric comparisons are real: Sandy Koufax looks a lot like a peak Greg Maddux, but Maddux's longevity makes him look less like Koufax in return. The two-way split surfaces that asymmetry instead of hiding it.

Scores decay exponentially with distance. Similar players cluster tightly; dissimilar ones don't score at all rather than scoring low. The goal was to avoid a long tail of meaningless 30% matches that just add noise.

---

## Era adjustments

The comparison chart has an era-adjusted toggle that switches between raw stats and adjusted equivalents: OPS+ for hitters, ERA+ for pitchers. Both are normalized to 100 as league average, which puts Ruth's dead-ball numbers and Bonds's steroid-era numbers on the same scale. This is the standard approach and it handles the bulk of the era problem cleanly.

The similarity engine itself uses adjusted metrics as its input, not raw stats. A player's similarity score reflects their adjusted production, not their counting numbers. This means the engine doesn't reward players for playing in a run-scoring environment and doesn't penalize pitchers who played in the 60s.

Qualification thresholds are applied before any comparison. A player with 50 career plate appearances isn't in the similarity pool. The cutoffs are documented on the methodology page and explained rather than hidden.

The aging curve overlay is pulled from positional averages by age, displayed with confidence tiers. It answers the natural follow-up question when you're looking at a career arc: is this player aging normally, ahead of the curve, or declining early? The tiers fade to indicate how much variance there is at the extremes of age, where sample sizes shrink.

---

## Where the numbers diverge from bWAR and fWAR

Baseball Reference and FanGraphs publish their own WAR numbers. They disagree with each other regularly, sometimes by 1-3 WAR per season for the same player. I use bWAR as the primary input for this tool, which is a choice worth being explicit about.

The methodology page documents the specific places where my outputs diverge from BBref's. Some divergences are intentional: I apply different qualification thresholds for the similarity pool than BBref uses for its leaderboards, because I'm optimizing for meaningful comparisons rather than comprehensive coverage. Some are downstream of data availability: the Statcast-era pitch zone panels only cover 2015 forward, and I'd rather show nothing than show something fake.

On that point: an earlier version of this tool had a monthly heatmap panel that looked great and generated its data from a seeded RNG. I removed it. A data tool that fabricates data to fill visual space is not a data tool. The empty panel is more honest than the plausible-looking chart.

---

## What I'd do differently

The similarity engine uses a fixed weight vector. The weights were chosen by hand based on domain knowledge and tuned against a set of known comparisons (players I'd expect to match). That works, but it's not principled. A better approach would be to learn the weights from a labeled dataset of "these two players are similar / these two are not," either through a regression or a learned embedding model. The current approach is good enough to be useful but shouldn't be mistaken for the right answer.

The era adjustment on the similarity side uses adjusted rate stats but not adjusted counting stats. Peak WAR by season is era-adjusted, but career totals are not reweighted for schedule length (teams played fewer games in the early 20th century). Comparing a 162-game modern player to a 154-game historical one means the modern player's career totals are structurally inflated. This is documented but not corrected, and correcting it properly would require rebuilding the ingest pipeline to apply season-length normalization before aggregation.

The pitch zone panels and Statcast-based features have a hard wall at 2015. Pre-Statcast players get no zone data. The tool is honest about this, but it does mean the product is genuinely less interesting for historical players, which is a real gap for a tool about cross-era comparison.

---

## Engineering notes

The backend is Django with a Postgres database, deployed on Railway. The ingest pipeline handles data from Baseball Reference and Statcast, with retry/backoff, idempotency, and 53 tests covering the critical paths. Similarity scores are recomputed on a schedule after each stats refresh, with dependency ordering enforced (similarity runs after stats, not concurrently). The scheduled jobs include failure alerting and staleness detection, so the app knows when its data is stale and says so rather than serving confidently wrong numbers.

The frontend is React with TypeScript, Visx for charts, and TanStack Query for data fetching. The chart library choice (Visx over something like Recharts) was made because this project's chart requirements are specific enough that a lower-level primitive-based library is easier to control than fighting a higher-level abstraction. Skeleton loading states are in place throughout and performance was explicitly tuned: no flicker on metric switches, prefetch on hover for leaderboard rows, no jank.

The full methodology is documented at [pcav2-production.up.railway.app](https://pcav2-production.up.railway.app), linked from the footer. If you're interested in the similarity weights, era cutoffs, or where the numbers diverge from standard references, that's the place to go.
