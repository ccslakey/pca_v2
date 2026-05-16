# Hall of Fame Metrics

Each player profile displays three scores derived from Bill James's Hall of Fame measurement system: **Black Ink**, **Gray Ink**, and **HOF Monitor**. These are displayed as a cluster on the profile stat grid. They're useful for understanding a player's historical footprint — how often they led the league or finished in the top 10 — and as a rough predictor of Hall of Fame worthiness.

None of these are our own invention. They are our implementation of James's published formulas, cross-checked against Baseball Reference's published figures.

---

## Black Ink

Black Ink counts **weighted points for leading the league** in various statistical categories. The name comes from the old practice of bolding league-leading figures in statistical tables.

### Batting Black Ink categories and weights

| Category | Points for leading |
|---|---|
| HR, RBI, batting average | 4 pts each |
| Runs, hits, slugging % | 3 pts each |
| Doubles, walks, stolen bases | 2 pts each |
| Games, at-bats, triples | 1 pt each |

### Pitching Black Ink categories and weights

| Category | Points for leading |
|---|---|
| Wins, ERA, strikeouts | 4 pts each |
| Innings pitched, WHIP | 3 pts each |
| Games started, complete games, shutouts | 2 pts each |
| Games (total), saves | 1 pt each |

**Qualification:** Rate stats (BA, OBP, SLG, OPS for batters; ERA, WHIP for pitchers) require **≥ 502 PA** or **≥ 162 IP** in that season to be eligible for the league-leading bonus.

**Typical Hall of Famer range:** Batters average ~27 Black Ink; pitchers ~40. A batter with 100+ Black Ink points (Babe Ruth, Ted Williams) is historically rare and almost certainly a first-ballot inductee.

---

## Gray Ink

Gray Ink counts **1 point for each top-10 finish** across a broader set of categories. It captures consistency and longevity that Black Ink misses — a player who never led the league but finished in the top 10 for 15 years accumulates substantial Gray Ink.

### Batting Gray Ink categories

HR, RBI, batting average, runs, hits, slugging %, OBP, doubles, triples, walks, stolen bases, games, at-bats, OPS, total bases.

### Pitching Gray Ink categories

Wins, ERA, strikeouts, innings pitched, WHIP, games started, complete games, shutouts, games (total), saves.

Same qualification rules as Black Ink for rate stats.

**Typical Hall of Famer range:** Batters average ~144 Gray Ink; pitchers ~185.

---

## HOF Monitor

The HOF Monitor is a composite predictor, not just an ink count. It incorporates Black and Gray Ink, career milestones, postseason performance, and award wins. A score of **100 is the threshold Bill James associated with likely Hall of Fame election.**

The HOF Monitor formula is more complex than the ink scores — it weights different career achievements on a point scale calibrated against historical inductees. Our implementation follows the formulas as published by James and documented on Baseball Reference's methodology pages.

---

## Divergences from Baseball Reference

Our computed scores will typically match BBref within ±1–2 points. Known sources of divergence:

- **Tie-breaking:** when two players are tied for a league lead or top-10 finish, different implementations may handle the tie differently (split the points, award full points to both, or award to neither). We award full points to all tied players.
- **Historical data coverage:** if our database is missing a season or has a slightly different value for a historical statistic, the ranking in that category shifts.
- **Qualification cutoffs:** we use 502 PA and 162 IP exactly; BBref's cutoff may differ slightly by era.

If you find a player whose scores diverge from BBref by more than 3–4 points, it's most likely a data coverage issue in that player's historical record.
