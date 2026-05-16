# Similarity Engine

The similar players panel on each profile page is powered by a custom similarity engine: a role-split, weighted-Euclidean k-NN over z-scored career features with a pool-calibrated score. No embedding model. Pure math.

---

## Two separate pools — batters and pitchers

A player who batted and pitched (Ohtani, Ruth) gets compared in both pools and returns both lists. Pool eligibility requires **career WAR ≥ 1.0** at that role. Below that threshold the sample is too thin to produce meaningful comps.

---

## Feature vector per player

**Batters (6 features):** career WAR · peak single-season WAR · career OPS+ (PA-weighted) · HR rate per 600 PA · position defensive value · position kind

**Pitchers (6 features):** career WAR · peak single-season WAR · career ERA+ (IP-weighted) · K/9 · starter % (GS÷G) · saves rate (saves per relief appearance)

### Why these features

WAR captures total value. Peak WAR captures dominance shape — two players with the same career WAR can have very different profiles if one had one transcendent peak and the other was consistently good for 15 years. OPS+/ERA+ are era-adjusted so 1908 Cy Young is comparable to 2018 Verlander. The role/style features keep sluggers from matching with slap hitters and starters from matching with closers.

### Position encoding (batters)

Two axes capture where a player sits on the defensive spectrum:

- **pos_value** (0–1): defensive difficulty. C = 1.0, SS = 0.8, 2B/CF = 0.7, 3B = 0.6, RF/LF = 0.4, 1B = 0.2, DH = 0.0.
- **pos_kind** (−1 to +1): corner vs. up-the-middle. C/SS/2B/CF = +0.5→+1.0; 3B = 0; RF/LF/1B/DH = −0.5→−1.0.

Both are weighted at 0.8 — meaningful, but subordinate to WAR and OPS+. Without them, catchers match with corner outfielders and first basemen match with shortstops.

### Closer encoding (pitchers)

`saves_rate` (saves ÷ relief appearances) distinguishes closers from setup and middle relievers without a hard threshold. Rivera and Hoffman score high; middle relievers score near zero; pure starters are set to 0. Weight 0.6 — lighter than WAR or ERA+ but enough to cluster Rivera with Wagner and Papelbon rather than with setup men who had the same career WAR.

---

## Z-scoring

Each feature is z-scored across the full pool: the difference between two players on any feature is divided by that feature's standard deviation across all pool members. This puts career WAR (ranging 0–160) and starter % (ranging 0–1) on the same scale before distance is computed.

---

## Weighted Euclidean distance

```
distance = sqrt(Σ weight_i × ((target_i − candidate_i) / stdev_i)²)
```

| Role | Weights |
|---|---|
| **Batters** | WAR 2.0 · Peak 1.0 · OPS+ 1.5 · HR rate 0.8 · pos_value 0.8 · pos_kind 0.8 |
| **Pitchers** | WAR 2.0 · Peak 1.0 · ERA+ 1.5 · K/9 1.0 · SP% 0.8 · saves_rate 0.6 |

Career WAR dominates. Era-adjusted rate stats are second. Style and shape features follow.

---

## Calibrated similarity score

Raw Euclidean distance is a unitless number that means nothing to a reader. To produce the 0–100 score shown in the panel:

1. Compute distances from the target to every candidate in the pool.
2. Find the **median distance** across all candidates.
3. Solve for a decay constant `k` such that the median candidate scores exactly **30**.
4. Score each candidate: `100 × exp(−k × distance)`.

This anchors the scale to the population: the median comp always scores ~30, a near-identical player scores ~90–95, and a dissimilar player trails off toward 0. **Scores are relative to the pool, not absolute.** A 90 for a catcher means "very close to this target among all catchers in the database," not "90% similar in some universal sense." Scores for two different target players are not directly comparable.

---

## What gets returned

Top 8 candidates per role are ranked. If a player record is missing from the database, the engine falls back to the next-best. Final list is **4 comps per role**. Players are excluded from their own comp list.

---

## Performance

Batting and pitching aggregate data are cached for one hour. The first call after a stats refresh pays the cost of ~2 database queries over all seasons; subsequent calls are dictionary lookups and arithmetic. At current database size, the computation takes under 100ms on cache miss.

---

## Known limitations

**No career-stage matching.** The engine compares career totals only. "Who was Mike Trout most like at age 24?" is unanswerable — the engine has no concept of career stage. Baseball Reference's similarity tool offers this; ours does not yet.

**Defense and baserunning are implicit.** WAR encodes both, but they're not separate features. A player who built their WAR through elite defense looks identical to a player who built it through power — the engine can't distinguish them.

**No era cohort filter.** Era-adjustment via OPS+/ERA+ means Cy Young can validly match Pedro Martínez, but the engine can't answer "modern era only." No soft penalty for debut-year distance exists.

**Score is relative, not absolute.** See the calibration section above. A 90 in a tightly clustered pool (e.g., modern high-OPS+ sluggers) is a tighter match than a 90 in a sparse pool (e.g., dead-ball power hitters). This is by design, but it means comparing scores across targets is imprecise.

---

## Comparison to Baseball Reference's Bill James method

BBref's method starts at 1,000 points and deducts for counting-stat deltas with a positional adjustment. It is more interpretable and generally produces sensible comps, but it is **not era-adjusted** — its matches skew toward contemporaries. A 1950s first baseman will match other 1950s first basemen almost regardless of quality.

Our method is era-adjusted and WAR-anchored. It finds the player who had the most similar career shape and production level, regardless of era. The tradeoff is interpretability: we can tell you the score but not which specific features drove it.
