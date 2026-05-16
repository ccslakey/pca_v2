# Known Divergences from Baseball Reference

This site aims for accuracy, but we are not Baseball Reference. Several methodological choices and data limitations create cases where our numbers will differ from what BBref shows. This page documents the known divergences so you can interpret discrepancies correctly.

---

## Career WAR

**Expected divergence: < 0.1 WAR for most players.**

Our career WAR is a sum of season-level bWAR values scraped from BBref. Minor differences can arise from:

- **Rounding:** BBref displays WAR to one decimal place. Summing rounded values can differ from their internally stored figures by ±0.1–0.2 over a long career.
- **Data vintage:** if a player's historical WAR was retroactively adjusted by BBref (they do this occasionally as their methodology improves), and we haven't re-ingested that player's data, our figure will reflect the old value.

If you see a career WAR that differs from BBref by more than 0.5 for a player with a long career, it likely reflects a re-ingestion lag. Report it and we'll refresh the player's data.

---

## Career OPS+ and ERA+

**Expected divergence: 0–3 points for most players; potentially more for short-career players.**

BBref computes career OPS+ and ERA+ from **career-level totals** against career-level league averages. We compute them as **PA-weighted (or IP-weighted) averages of season-level figures**. For players with long, consistent careers the two methods agree closely. Divergences grow for:

- Players with very short careers (one outlier season has outsized weight in either method)
- Players whose careers straddle major offensive era shifts (e.g., playing through both the pitcher-dominated late '60s and the high-offense '70s)
- Players with extreme park factors in specific seasons

---

## Bill James Scores (Black Ink, Gray Ink, HOF Monitor)

**Expected divergence: ±1–3 points.**

Sources of divergence from BBref's published figures:

- **Tie-breaking:** we award full points to all players tied for a league lead or top-10 finish. BBref may handle ties differently in some categories.
- **Historical stats:** if our database has a slightly different value for an older statistic (batting average or ERA in the 1890s, for example), rankings in that category will shift.
- **HOF Monitor formula:** some components of the HOF Monitor are not fully documented publicly. Our implementation follows the published version of James's formula; edge cases in the weighting may diverge from BBref's proprietary implementation.

---

## Primary Position

**This field can diverge from how a player is commonly known.**

Primary position is assigned algorithmically from BBref's `*` marker data. It reflects the position where a player accumulated the most primary-season designations, which may not match fan perception. Common cases:

- A player known as a shortstop who moved to third base late in their career may be classified as 3B if the late-career seasons are numerous enough.
- A pitcher who also DHed may be classified as DH rather than P depending on the season count.

This affects leaderboard filters. If you expect a player to appear under a position filter and they don't, check their profile page for their assigned primary position.

---

## Similarity Scores

The similar players panel is **our own engine, not BBref's Bill James similarity scores.** The two systems produce different comps for the same player and should not be compared directly. See the [Similarity Engine article](/methodology/similarity) for methodology details.

---

## Pitch Zone Data

The pitch zone heatmap is derived from Statcast via Baseball Savant, not Baseball Reference. Rates shown (contact %, hit %, whiff %) are computed from our aggregated bucket data. Slight differences from Baseball Savant's own zone visualizations may reflect differences in how zone boundaries are defined or how coordinates are binned.

---

## A note on "correct"

bWAR, fWAR, and Statcast-based WAR all measure the same concept with different methodologies and legitimately produce different answers. BBref's own figures change over time as their methodology evolves. There is no single "correct" version of most advanced baseball statistics — there are better and worse implementations of specific frameworks. Where we differ from BBref, this page documents why. Where you disagree with the methodology, the [Similarity Engine](/methodology/similarity), [WAR](/methodology/war), and [Era-Adjusted Metrics](/methodology/era-adjusted-metrics) articles explain our choices.
