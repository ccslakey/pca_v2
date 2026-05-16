# WAR: Source & Scope

All WAR values on this site are **bWAR** — Baseball Reference's version of Wins Above Replacement. This is a deliberate choice, not a default, and it affects what the numbers mean.

---

## Which WAR, and why

Three major WAR systems exist: bWAR (Baseball Reference), fWAR (FanGraphs), and rWAR (they're the same thing). A fourth, Baseball Savant's oWAR/dWAR, is newer and Statcast-based.

We use bWAR because:

- It covers **1871–present** — the longest historical scope of any public WAR system. This matters for a cross-era comparison tool.
- Its defensive component uses **Defensive Runs Saved** and Total Zone (pre-DRS era), giving reasonable estimates back to the dead-ball era.
- It is the WAR system most commonly cited in mainstream baseball writing, so users have the most intuition for what the numbers mean.

fWAR is a legitimate alternative. It uses UZR for defense (generally considered more reliable than DRS in the recent era) and a slightly different batting run calculation. The two systems agree closely for most players — within 1–2 WAR over a career — but diverge more for players with extreme defensive profiles or very long careers. Neither is definitively correct; they measure the same concept with different methodologies.

If you see a career WAR figure here that differs from a number you've seen elsewhere, check which system the other source used.

---

## What bWAR measures

One unit of WAR represents the value a player added above what a freely available replacement-level player would have produced — roughly the level of a AAAA player or a bench/bullpen depth piece. A player worth 2 WAR per season is a solid regular; 5+ is an All-Star caliber season; 8+ is an MVP-level season.

bWAR is the **sum** of:
- **Batting runs** (park- and league-adjusted)
- **Baserunning runs**
- **Fielding runs** (position-adjusted)
- **Positional adjustment** (catchers and shortstops get credit for playing harder positions)
- **Replacement level adjustment**

All components are converted to a common run scale and then divided by runs-per-win for the relevant season.

---

## Career WAR on this site

Career WAR shown in charts and player cards is the **sum of all season WAR values** in the database, including partial seasons and short stints with multiple teams. It includes both batting and pitching contributions for two-way players.

Negative season WAR values are included. A player who was below replacement level in a season contributes a negative number to career total.

---

## Era and replacement-level context

Replacement level is calibrated per era — a 5-WAR season in 1910 and a 5-WAR season in 2010 represent roughly equivalent value above replacement for that era. This is a core feature of WAR and why it's useful for cross-era comparison.

However, **schedule length matters**. A player in the 154-game schedule era (pre-1961) had fewer opportunities to accumulate counting WAR than a player in the 162-game era. This affects career totals more than rate-of-production comparisons.
