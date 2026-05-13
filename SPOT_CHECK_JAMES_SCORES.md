# Spot-checking the James Scores

How to verify that `compute_james_scores` produces numbers that line up with Baseball Reference's published values, and what to do when they don't.

---

## Where BBref publishes these

For any player, the URL is `https://www.baseball-reference.com/players/<first letter>/<bbref_id>.shtml`. Scroll to the section called **"Hall of Fame Statistics"** (or similar — sometimes labeled "James Hall of Fame Monitor"). It shows all three numbers:

- **HOF Monitor** — typically the second or third row
- **Black Ink** — labeled as "Black Ink Batting" or "Black Ink Pitching"
- **Gray Ink** — same

If you don't see them, expand any "show more" toggles in that section.

---

## Current computed values for 30 reference players

Run the command and dump current values:

```bash
python manage.py shell -c "
from players.models import Player
from stats.models import JamesScore
SAMPLES = [
    ('ruthba01','Babe Ruth'), ('aaronha01','Hank Aaron'), ('mayswi01','Willie Mays'),
    ('cobbty01','Ty Cobb'), ('willite01','Ted Williams'), ('bondsba01','Barry Bonds'),
    ('musiast01','Stan Musial'), ('mantlmi01','Mickey Mantle'), ('schmimi01','Mike Schmidt'),
    ('gwynnto01','Tony Gwynn'), ('ripkeca01','Cal Ripken'), ('benchjo01','Johnny Bench'),
    ('troutmi01','Mike Trout'), ('pujolal01','Albert Pujols'), ('jeterde01','Derek Jeter'),
    ('suzukic01','Ichiro Suzuki'), ('cabremi01','Miguel Cabrera'), ('rosepe01','Pete Rose'),
    ('palmera01','Rafael Palmeiro'),
    ('youngcy01','Cy Young'), ('johnswa01','Walter Johnson'), ('clemero02','Roger Clemens'),
    ('johnsra05','Randy Johnson'), ('maddugr01','Greg Maddux'), ('martipe02','Pedro Martinez'),
    ('seaveto01','Tom Seaver'), ('koufasa01','Sandy Koufax'), ('riverma01','Mariano Rivera'),
    ('kershcl01','Clayton Kershaw'), ('verlaju01','Justin Verlander'),
]
print(f'{\"Player\":25} {\"BlkBat\":>6} {\"GryBat\":>6} {\"HOFBat\":>6}  {\"BlkPit\":>6} {\"GryPit\":>6} {\"HOFPit\":>6}')
for bid, name in SAMPLES:
    try:
        js = Player.objects.get(bbref_id=bid).james_score
        print(f'{name:25} {js.black_ink_bat:>6} {js.gray_ink_bat:>6} {js.hof_monitor_bat:>6}  {js.black_ink_pit:>6} {js.gray_ink_pit:>6} {js.hof_monitor_pit:>6}')
    except Exception:
        print(f'{name:25} -- not found --')
"
```

---

## What to spot-check

For each of the 30 reference players, fill in BBref's published value vs. ours:

| Player | Score | BBref | Computed | Δ | Notes |
|---|---|---|---|---|---|
| Babe Ruth | HOF Monitor (bat) |  | 328 |  |  |
| Babe Ruth | Black Ink (bat) |  | 135 |  |  |
| Babe Ruth | Gray Ink (bat) |  | 126 |  |  |
| Hank Aaron | HOF Monitor (bat) |  | 385 |  |  |
| Hank Aaron | Black Ink (bat) |  | 42 |  |  |
| Hank Aaron | Gray Ink (bat) |  | 145 |  |  |
| ... | ... | ... | ... | ... | ... |

You don't need to check every player — focus on **10–15 with a mix of**:

- **Pure batters** (Aaron, Mays, Williams, Gwynn, Ripken, Trout)
- **Power hitters** (Ruth, Bonds, Schmidt, Pujols)
- **Position players where defense matters** (Bench at C, Ripken at SS)
- **Modern players** (Trout, Cabrera, Kershaw)
- **Closers** (Rivera) ← this is where my formula is most uncertain
- **Pure starters across eras** (Cy Young, Maddux, Koufax, Verlander)

---

## How to interpret discrepancies

### "Our number is consistently higher"
Most likely cause: one of the **per-season cap** values is too generous. The biggest knobs:

- **All-Star points** (currently 3 pts each, cap 20) — BBref sometimes uses 1 pt each
- **Batting title points** (currently 6 each) — some implementations use 3 or 4
- **Gold Glove points** (currently 2 each, uncapped) — some cap this at 16 or 8
- **Position bonus for non-catcher infielders** (currently 30) — could be 15
- **100-R / 100-RBI / 200-H season caps** (currently 8 / 8 / 4) — could be lower

In `compute_james_scores.py`, search for the section labeled `# --- Awards ---` and `# --- 100 RBI seasons ---` to find these.

### "Our number is consistently lower"
Most likely cause: a **threshold** is too high, or we're missing a category.

- **Hits / HR / RBI thresholds** in `_hof_monitor_batter` — verify they match James's
- **Saves thresholds** in `_hof_monitor_pitcher` — closers may be undervalued (e.g., Rivera came out at 61, BBref shows ~180+)
- **No-hitter / perfect-game bonuses** — we don't have this data ingested, so we can't award those points

### "Black/Gray Ink looks wrong"
Check whether you're qualifying correctly. We use **502 PA / 162 IP** as the modern qualifier, which means:
- Pre-1961 seasons (154 games) will under-qualify slightly
- Strike-shortened years (1981, 1994, 1995, 2020) will under-qualify by a lot
- Career players in those years may show artificially low rate-stat ink

If this matters for the players you're checking, we can either lower the qualifier or make it era-aware.

### "Specific player is off but everyone else is fine"
Probably a data issue, not a formula issue. Check:
1. Are their season totals correct in the DB? (`p.batting_seasons.values_list('year','at_bats','hits','home_runs')`)
2. Is their `primary_position` correct? (Position bonus changes the score by 30–60)
3. Are their awards counted? (`p.awards.values('kind')`)

---

## Adjusting the formula

Every constant lives in **one place**: `stats/management/commands/compute_james_scores.py`. After editing:

```bash
python manage.py compute_james_scores
```

The command rebuilds the whole `JamesScore` table from scratch (~10 seconds). Re-run the spot-check shell snippet, compare to BBref again.

The most-likely-to-tune knobs, with their current values:

```python
# Black/Gray ink categories — formula intentionally matches James 1986
BAT_BLACK_INK_CATEGORIES = [("hr", 4), ("rbi", 4), ("ba", 4), ...]

# Awards in _hof_monitor_batter:
pts += 8 * awards.get("mvp", 0)            # try 12 if MVPs look light
pts += min(20, 3 * awards.get("asg", 0))   # try min(15, 1 * ...) if All-Stars feel heavy
pts += 2 * awards.get("gg", 0)             # try 1 each if Gold Gloves dominate
pts += 6 * awards.get("bat_title", 0)      # try 3 each if batting titles feel heavy

# Position bonus:
if primary_position == "C":           pts += 60   # established
elif primary_position in {"2B","SS","3B"}: pts += 30   # try 15 if position players over-score
elif primary_position == "CF":        pts += 15   # James didn't have this; try 0 if CFs over-score
```

For pitchers, the most uncertain part is **closer scoring**. Rivera should land around 175 on HOF Monitor; if he's coming out lower, increase the saves thresholds:

```python
if sv >= 600:    pts += 40   # try 75 — Rivera is the GOAT closer
elif sv >= 400:  pts += 25
elif sv >= 300:  pts += 10
```

---

## Calibration target

You don't need to match BBref to the single digit. Aim for:

- **HOF Monitor**: within 10–15% of BBref's value for clear HOFers (Ruth, Mays, Aaron, etc.)
- **Black Ink / Gray Ink**: within 5–10% — these are simpler formulas, less ambiguous
- **Borderline candidates** (HOFM 80–120): try to be within 5 points absolute

If multiple players are off in the same direction by the same amount, that's a knob to tune. If players are off in random directions, the data may have issues or it's per-player edge cases — not worth chasing.

---

## Notes on data limitations

A few facts that may cause expected differences from BBref:

- **No postseason stats ingested** — Rivera's HOF Monitor will be lower than BBref's because he gets ~30+ points from postseason saves in their formula
- **No no-hitter / perfect-game data** — small effect, but Ryan and Koufax will be lower
- **Modern strike-shortened seasons** — see qualifier discussion above
- **Pre-1900 league leadership** — many categories were tracked differently; old-timer ink scores may diverge

If any of these matter for your demo, we can add the missing pieces — but most portfolio viewers won't notice.
