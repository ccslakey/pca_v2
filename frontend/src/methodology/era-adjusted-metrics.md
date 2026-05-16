# Era-Adjusted Metrics: OPS+ and ERA+

OPS+ and ERA+ appear throughout the site wherever raw counting stats would mislead cross-era comparisons. Both are park- and league-adjusted, scaled so that 100 always means exactly league average for that season.

---

## OPS+

**OPS+ = 100 × (OBP / lgOBP + SLG / lgSLG − 1) / park factor**

A value of 100 is league average. Every point above 100 is one percentage point better than average; every point below is one worse. Ted Williams's career OPS+ of 190 means he was 90% better than the average hitter across his career — a figure that accounts for the fact that the leagues he played in varied in their offensive environments.

Key properties:
- **Park-adjusted:** hitters in Coors Field and Fenway are measured against the run environment those parks create, not the neutral league average.
- **Era-adjusted:** a 150 OPS+ in 1968 (the "Year of the Pitcher") and a 150 OPS+ in 2000 (the steroid era's offensive peak) represent equal dominance over peers, even though the raw slash lines look nothing alike.
- **Not age-adjusted:** a player's OPS+ declines naturally with age; the metric doesn't correct for that.

### How we calculate career OPS+

Career OPS+ on this site is a **PA-weighted average** of season OPS+ values. This is more accurate than summing OPS and re-adjusting, but it differs slightly from Baseball Reference's published career OPS+, which computes the career figure from career totals against career-level league averages. For most players the difference is under 1 point. For players with very short careers or who straddle eras, it can be 2–3 points.

---

## ERA+

**ERA+ = 100 × (lgERA / ERA) × park factor**

ERA+ is inverted from ERA — **higher is better**. A 100 ERA+ is exactly league average. Pedro Martínez's 2000 season (ERA+ of 291) is the highest single-season ERA+ in modern history; he was nearly three times better than the average pitcher that year.

Key properties:
- **Park-adjusted:** pitchers in hitter-friendly environments get credit for the context they pitched in.
- **Era-adjusted:** a 150 ERA+ during the dead-ball era and a 150 ERA+ during the steroid era represent equivalent dominance.
- **Not innings-adjusted:** a closer can post a high ERA+ in 60 innings that a starter couldn't sustain over 200. We use starter % as a separate feature in the similarity engine to account for workload shape.

### How we calculate career ERA+

Career ERA+ is an **IP-weighted average** of season ERA+ values (IP measured in outs recorded). Same reasoning as OPS+: weighting by workload prevents a dominant 10-inning cup of coffee from distorting a career figure. Same caveat: small divergences from Baseball Reference's published career figure are expected and normal.

---

## Why these metrics matter for cross-era comparison

A tool that compares 1927 Babe Ruth with 2001 Barry Bonds cannot use raw statistics honestly. The offensive environments, park dimensions, talent pool, and schedule lengths were all different. OPS+ and ERA+ remove those environmental confounds, leaving a measure of "how much better than your peers were you?" — which is a question you can answer across any era.

This is also why the similarity engine uses OPS+ and ERA+ as primary rate features rather than raw batting average, OBP, SLG, or ERA.
