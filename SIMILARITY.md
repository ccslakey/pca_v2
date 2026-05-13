# Similarity Algorithm

Documentation for the engine in `players/similarity.py`. Seed doc for the eventual public methodology page (Threshold 2 in [`RELEASE_ROADMAP.md`](RELEASE_ROADMAP.md)).

---

## In one line

A role-split, weighted-Euclidean k-NN over z-scored features with a pool-calibrated similarity score. Pure math; no embedding model.

---

## How it works

### 1. Two separate pools — batters and pitchers
A player who batted and pitched (Ohtani, Ruth) gets compared in both pools and the response returns both lists.

Pool eligibility: a player is in the pool only if they have **career WAR ≥ 1.0** at that role.

### 2. Feature vector per player
- **Batters (6 features):** career WAR, peak single-season WAR, career OPS+ (PA-weighted), HR rate per 600 PA, position defensive value, position kind
- **Pitchers (6 features):** career WAR, peak WAR, career ERA+ (IP-weighted), K/9, starter % (`GS/G` — 0 = pure reliever, 1 = pure starter), saves rate (saves per relief appearance)

Why these: WAR captures total value, peak WAR captures dominance shape, OPS+ / ERA+ are era-adjusted so 1908 Cy Young is comparable to 2018 Verlander, and the role/style stats keep sluggers from matching with slap hitters and starters from matching with closers.

**Position embedding (batters):** Two-axis encoding of where a player sits on the defensive spectrum. `pos_value` (0–1) measures defensive difficulty: C=1.0, SS=0.8, 2B/CF=0.7, 3B=0.6, RF/LF=0.4, 1B=0.2, DH=0.0. `pos_kind` (−1 to +1) captures corner vs. up-the-middle: C/SS/2B/CF = +0.5→+1.0; 3B = 0; RF/LF/1B/DH = −0.5→−1.0. These two axes prevent catchers from matching with corner outfielders and first basemen from matching with shortstops. Weight 0.8 each — meaningful but subordinate to WAR and OPS+.

**Closer vs. setup embedding (pitchers):** `saves_rate` (saves ÷ relief appearances) distinguishes closers from setup and middle relievers without hard thresholds. Rivera/Hoffman score high; middle relievers score near zero; pure starters are set to 0. Weight 0.6 — lighter than WAR or ERA+ but enough to cluster Rivera with Wagner/Papelbon rather than setup men.

**Primary position data note:** `primary_position` is derived from Baseball Reference fielding data using BBref's `*` primary-season marker. It reflects the position a player appeared at most often as their designated primary role by season count. Known edge cases: multi-position players and DH-heavy late careers may not match the position the player is commonly identified with.

### 3. Z-score each feature across the pool
Standard deviation of each feature is computed across the whole pool. Differences are then divided by stdev so all features sit on the same scale — career WAR (~0–160) and SP% (0–1) get treated comparably.

### 4. Weighted Euclidean distance
```
distance = sqrt(Σ weight_i × ((target_i − candidate_i) / stdev_i)²)
```
Weights bias what "similar" means:

| Role | Weights |
|---|---|
| **Batters** | WAR 2.0 · Peak 1.0 · OPS+ 1.5 · HR rate 0.8 · pos_value 0.8 · pos_kind 0.8 |
| **Pitchers** | WAR 2.0 · Peak 1.0 · ERA+ 1.5 · K/9 1.0 · SP% 0.8 · saves_rate 0.6 |

Career WAR dominates, era-adjusted rate stats second, role/peak less.

### 5. Calibrated similarity score (the clever bit)
Raw distance is a meaningless number. To turn it into a 0–100 percentage, the code:
- Finds the **median distance** across all candidates in the pool
- Picks a decay constant `k` so that the median candidate scores exactly **30**
- Final score: `100 × exp(-k × distance)`

This means the score is **relative to the population**: top matches are ~85–95, the median player is always ~30, dissimilar players trail off toward 0. A 95 means "very close in this pool"; 30 means "median similar"; not an absolute distance.

### 6. Top 4 returned per role
The top 8 are ranked; hydration falls back to the next-best if a player record is missing; final list is 4 per role.

### Performance
Aggregates are cached for an hour (`_CACHE_TTL = 3600`). First call after a stats refresh pays the cost (~one query per stat over all seasons); subsequent calls are dict lookups + math.

---

## Gaps / not yet implemented

These are the known limitations of the current engine. Each is a candidate for the methodology doc and/or a future roadmap item.

### Career-stage matching ("similar through age N")
The biggest gap. BBref's similarity tool shows comps both at career-total level *and* "through age N." Hugely useful — "who was Mike Trout most like at age 24?" is the canonical prospect-comp question. We only do career totals. Implementation would swap career totals in `_load_*_agg()` for seasonal totals up to a given age.

### Defense and baserunning
WAR encodes both implicitly, but we don't have them as explicit features. A player who racked up WAR via slugging and a player who racked up the same WAR via glove + speed look identical to the engine.

### No era cohort weighting
Era-adjusted via OPS+ / ERA+, but the engine can't answer "modern era only" — Cy Young can match Pedro Martinez fine. Would need either a filter parameter or a soft penalty on debut-year distance.

### Pitcher style is partial
SP% + saves_rate now distinguish starters, closers, and mid-relievers, but not workload shape within starters (innings-eater vs. spot starter), pitch arsenal, or velocity profile. K/9 carries most of the "stuff" signal, which is coarse.

### Similarity is not stored
Recomputed on every cache miss. Cache is one hour; after that, the first request rebuilds the aggregates over the whole DB. Could persist to a `similarity` table keyed by (target_id, role) for instant reads, but the current latency is acceptable for the demo.

### Score is relative, not absolute
A score of 90 in a tightly clustered pool (modern OPS+ in the 130s) doesn't mean the same thing as 90 in a sparse pool (peak dead-ball power hitters). Median is anchored at 30 — that's the design — but it means scores across different targets aren't strictly comparable.

### No interpretability surface
The score comes out as a single number. No "Player X matches because their WAR profile is close and their HR rate is close, but their OPS+ is different" breakdown. Adding a feature-contribution view would help both demos and credibility with the sabermetrics audience.

### Pool filter is binary
`career WAR ≥ 1.0` keeps the pool clean but hides edge cases — a 0.9-WAR player who would be the closest match technically can't show up. A soft penalty rather than a hard cutoff would be more correct.

---

## Comparison to BBref's Bill James similarity scores

For methodology-page context. BBref's method (1000 points − counting-stat deltas with a positional adjustment) is more interpretable and position-aware out of the box, but **not era-adjusted** and **doesn't use WAR** — its matches skew toward contemporaries. Our method is era-adjusted and WAR-anchored at the cost of interpretability and absolute scale.

Honest framing for the public doc:
> BBref uses Bill James's 1986 counting-stat method — interpretable and position-aware but not era-adjusted. Ours is z-scored weighted Euclidean over WAR + era-adjusted rate stats, sacrificing interpretability for cross-era validity.
