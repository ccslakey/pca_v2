# Award Tracking

Award wins are displayed as glyphs on career arc charts and listed chronologically on player profile pages. This document describes which awards are tracked, how they're sourced, and how the chart resolves conflicts when a player wins multiple things in the same season.

---

## Awards tracked

| Award | Abbreviation | Notes |
|---|---|---|
| Triple Crown (batting) | TC | Tracked when a player leads their league in AVG, HR, and RBI |
| Triple Crown (pitching) | TC | Leads league in W, ERA, and SO |
| Most Valuable Player | MVP | League MVP only (ALCS/NLCS MVP is tracked separately as Postseason MVP) |
| Cy Young Award | CY | Awarded since 1956; one award for all of MLB 1956–1966, then split by league |
| World Series Champion | WS | Team award attributed to each roster player |
| Rookie of the Year | ROY | Since 1947; split by league since 1949 |
| Postseason MVP | PMVP | World Series MVP, ALCS MVP, NLCS MVP |
| Silver Slugger | SS | Since 1980 |
| Gold Glove | GG | Since 1957 |
| Batting Title | BAT | Seasonal league-leading batting average (qualified) |
| ERA Title | ERA | Seasonal league-leading ERA (qualified) |
| All-MLB Team | AMLB | Since 2019 |
| All-Star Game | ASG | All-Star selection per season |

**Hall of Fame induction** is stored in the database but not shown as a chart glyph — it's a career milestone, not a seasonal event.

---

## Data source

Award data is scraped from Baseball Reference. Year coverage follows what BBref has catalogued: most awards are complete to their first year of existence; All-Star Game selections are complete back to 1933 (the first Midsummer Classic).

---

## Glyph priority resolution

Each season on the chart shows **at most one glyph** per player. When a player wins multiple awards in the same season (e.g., MVP and batting title, or Cy Young and ERA title), the chart shows the highest-priority award. Priority order, lowest number wins:

| Priority | Award |
|---|---|
| 0 | Triple Crown (batting or pitching) |
| 1 | MVP |
| 2 | Cy Young |
| 3 | World Series |
| 4 | Rookie of the Year |
| 5 | Postseason MVP |
| 6 | Silver Slugger |
| 7 | Gold Glove |
| 8 | Batting Title / ERA Title |
| 9 | All-MLB Team |
| 11 | All-Star |

Triple Crown takes highest priority because it's the rarest achievement and subsumes the batting/ERA title it contains. The full list of awards won in a season is always visible in the season tooltip regardless of which glyph is displayed.

---

## What's not tracked

- **Minor league awards** — not in scope.
- **Historical awards given retroactively** — some organizations have honored players from eras before their award existed. We track awards only in the years they were officially given.
- **Individual statistical records** (e.g., single-season HR record) — not modeled as awards.
- **Manager of the Year** — applies to managers, not players.
