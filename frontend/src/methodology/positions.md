# Primary Position Assignment

Every player in the database has a `primary_position` field that determines how they're filtered in the leaderboard, which defensive encoding they get in the similarity engine, and what position is displayed in the profile hero block.

---

## How primary position is determined

Primary position is derived from **Baseball Reference fielding data** using BBref's own `*` (asterisk) marker. In BBref's season-level fielding tables, the position where a player appeared most often in a given season is marked with an asterisk. Our `primary_position` is the position that received the most `*` seasons across a player's career.

In the case of a tie (equal number of primary seasons at two positions), we default to the position higher on the defensive spectrum — so a player who split their career equally between left field and shortstop would be classified as SS.

---

## Known edge cases and limitations

**Multi-position players.** A true utility player who split time roughly evenly across several positions may have their primary position assigned in a way that doesn't match how fans or analysts would categorize them. The assignment is systematic, not editorial.

**DH-heavy late careers.** Players who spent the majority of their career at a fielding position but finished as a designated hitter — particularly common in the American League for aging power hitters — may be assigned their fielding position. DH has its own position code in the database and will be assigned as primary only if the player accumulated more `*`-seasons at DH than at any fielding position.

**Two-way players.** Shohei Ohtani is the obvious modern case. As a pitcher and a DH in the same seasons, his primary position assignment will depend on where BBref allocated the `*` marker for those seasons. Players like this appear in both the batting and pitching similarity pools regardless of their primary position field.

**19th-century and early-20th-century players.** Positional specialization was less rigid in the early game. Some early players switched positions frequently in ways that don't map cleanly onto the modern concept of a primary position. Their assignments are best-effort given the data.

---

## Position codes used

| Code | Position |
|---|---|
| C | Catcher |
| 1B | First Base |
| 2B | Second Base |
| 3B | Third Base |
| SS | Shortstop |
| LF | Left Field |
| CF | Center Field |
| RF | Right Field |
| P | Pitcher |
| DH | Designated Hitter |

The leaderboard position filter uses these codes directly. Selecting "SS" shows all players whose `primary_position` is SS — no fuzzy matching.
