# Pitch Zone Heatmaps

The pitch zone view on each player profile page shows where pitches were located and what happened at each location — either as a batter seeing pitches or as a pitcher throwing them. This data comes from Statcast and is only available for **2015 and later**.

---

## Data source and scope

Zone data is sourced from Baseball Savant via Statcast. Coverage begins with the 2015 season, when the TrackMan radar/camera system was installed in all 30 MLB parks. Players who retired before 2015 have no pitch zone data regardless of how distinguished their careers were.

For players who played before and after 2015 (e.g., a player with a career spanning 2010–2020), the zone view reflects only their Statcast-era seasons (2015–2020 in that example).

---

## How zones are constructed

Raw Statcast data records the plate location of every pitch in (x, z) coordinates measured in feet from the center of home plate. The coordinate system:
- **x:** horizontal position. Negative = catcher's left (batter's right); positive = catcher's right (batter's left).
- **z:** vertical height above the ground at home plate.

We aggregate pitch counts and outcome counts into spatial buckets by rounding plate_x and plate_z coordinates to 0.1-foot precision. The frontend bins these raw coordinates into a display grid at render time, producing the heatmap cells.

The strike zone boundaries displayed on the heatmap are approximate league averages (roughly 1.5–3.5 feet in height, 0.83 feet wide on each side of center). The actual called-strike zone varies by umpire, batter height, and stance.

---

## Outcomes tracked

Three outcome views are available per player-role:

| Tab | What it shows |
|---|---|
| **Contact** | Balls put in play (contact rate at each location) |
| **Hits** | Balls that became hits (hit rate at each location) |
| **Whiffs** | Swings and misses (whiff rate at each location) |

Each view is the **rate** for that outcome — contact / total pitches seen at that location, hits / total pitches seen, whiffs / total pitches seen — not the raw count.

---

## Color scale

The heatmap uses a blue → white → red scale:
- **Red (hot):** high rate of the selected outcome at that location.
- **Blue (cold):** low rate at that location.
- **White:** near average.

For a **batter**, red zones in the contact or hit view are favorable locations — the batter makes contact or gets hits there frequently. In the whiff view, red zones are unfavorable — the batter misses a lot there.

For a **pitcher**, the interpretation inverts: red in the contact/hit view is unfavorable for the pitcher; red in the whiff view is favorable.

---

## Sample size caveat

The heatmap shows data from all available Statcast seasons without a minimum pitch-count cutoff per cell. Low-traffic zones (extreme corners, way above the zone) may have very few pitches and therefore unreliable rates. A cell showing 0% hits at an extreme location might reflect 2 pitches, not a meaningful pattern. Use low-traffic zones with appropriate skepticism.

Players with fewer than 2 full Statcast seasons in the database may have sparse heatmaps overall.
