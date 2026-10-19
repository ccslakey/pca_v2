# PCA (Career Arc Visualizer) — building with this library

Baseball career-comparison UI. Components are the app's real ones, on `window.PCA`. Most take **player data objects** (shapes below), not children.

## Setup: always wrap in `AppProviders`

```jsx
const { AppProviders, PlayerCard } = window.PCA;
<AppProviders>{/* your screen */}</AppProviders>
```

`AppProviders` = React Query client + in-memory router + `ThemeProvider`. Without it, `MetricToggle`/`CareerArcPanel` throw (React Query), `PlayerCard`/`HeroSection`/`SimilarPlayersPanel`/`MobileTabBar` throw (`<Link>` needs a router), and `ThemePicker` throws (`useTheme`). `ThemeProvider` writes the active theme's CSS variables onto `<html>`. There are 8 themes (`THEMES`); the default follows `prefers-color-scheme`.

## Styling idiom: CSS variables + the app's own classes

No utility classes. For your own layout glue, use these tokens in inline styles:
- Surfaces/lines: `--bg-0`…`--bg-3`, `--line`, `--line-soft`
- Text: `--text-0` (strongest) … `--text-3` (faintest)
- Status: `--accent`, `--accent-2`, `--success`, `--danger`, `--warning`
- Series colors: `--chart-1`…`--chart-10`
- Type and shape: `--font-sans`, `--font-mono` (use it for numbers), `--font-display`, `--radius-sm`, `--radius`, `--radius-lg`, `--shadow-1`

Container classes that exist:
- Panel: `.panel` > `.panel-header` > `.panel-title` (with a `<span className="muted">` subtitle) + `.panel-action`
- Compare page: `.main`, `.chart-card` (card around charts), `.cards-row` (grid of `PlayerCard`s)
- Profile page: `.profile` > `.profile-main`, with `.col-2` (2fr/1fr grid)
- Mobile: `.m-app` (phone screen, positioned), `.m-card`, `.m-section`, `.m-section-title`

Do not invent other class names.

## Data shapes (the `.d.ts` files reference these)

```ts
type MetricId = 'war'|'hr'|'avg'|'ops'|'ops_plus'|'era'|'era_plus'|'so'; type XMode = 'year'|'age';
interface ChartSeason { season: number; age: number|null; war, hr, avg, ops, ops_plus, era, era_plus, so: number|null }
interface PlayerAward { id: number; year: number; kind: AwardKind; league: string|null; notes: string|null }
// AwardKind: 'mvp'|'cy'|'roty'|'gg'|'ss'|'tc_b'|'tc_p'|'hof'|'postmvp'|'bat_title'|'era_title'|'all_mlb'|'ws'|'asg'
interface ChartPlayer { id: string /* bbref id, e.g. 'troutmi01' */; name; color /* CSS color */; initials; pos /* 'CF','LHP','DH' */;
  years /* '1989–2010' | 'Active' */; seasons: ChartSeason[]; isBatter; isPitcher: boolean; awards: PlayerAward[];
  birthYear: number|null; warPercentile: {topPct, position, rank, n}|null }
type Peak = { season: number; val: number } | null;   // from peakSeason()
interface JamesScore { black_ink_bat, gray_ink_bat, hof_monitor_bat, black_ink_pit, gray_ink_pit, hof_monitor_pit: number }
interface SimilarPlayersResponse { batters: SimilarPlayer[]; pitchers: SimilarPlayer[] }
// SimilarPlayer: { bbref_id, first_name, last_name, debut, final_game, career_war, primary_position, throws, is_pitcher, similarity /* 0-100 */ }
```

Derive props with the exported helpers, as the app does: `peakSeason(seasons, metric)`, `careerWar(seasons)`, `sumMetric(seasons, metric)`, `fmtMetric(metric, v)`, `playerColor(id)` (profile color), `colorTint(color, alpha)`, and the constants `METRICS`, `MAX_PLAYERS` (10). On compare views, color players by slot as `var(--chart-N)`.

## Sizing rules

- `CareerChart`, `BrushChart` and `ProfileChart` need a numeric `width`.
- `Sparkline` and `CareerArcPanel` fill their parent, so give the parent a width.
- `MonthlyHeatmap` has `min-width: 600px`.
- `SeasonSheet` is an absolutely positioned bottom sheet, so put it inside `.m-app` with a fixed height.
- `MetricToggle`'s desktop layout needs about 1100px.

## Example: a profile column

```jsx
const { AppProviders, HeroSection, StatGrid, SeasonLogPanel, peakSeason, careerWar, sumMetric, playerColor } = window.PCA;
const color = playerColor(p.id), peak = peakSeason(p.seasons, 'war');
<AppProviders>
  <div className="profile"><div className="profile-main">
    <HeroSection player={p} color={color} jerseyNum={24} peak={peak} />
    <StatGrid player={p} war={careerWar(p.seasons)} peak={peak} careerHR={sumMetric(p.seasons,'hr') ?? 0}
      careerSO={sumMetric(p.seasons,'so') ?? 0} careerAVG={sumMetric(p.seasons,'avg')}
      careerOPS={sumMetric(p.seasons,'ops')} careerERA={sumMetric(p.seasons,'era')} />
    <div className="col-2">
      <SeasonLogPanel player={p} color={color} peak={peak} tab="standard" setTab={() => {}} />
      <div className="panel"><div className="panel-header"><div className="panel-title">Notes <span className="muted">your content</span></div></div></div>
    </div>
  </div></div>
</AppProviders>
```

Per-component usage and examples: `components/<group>/<Name>/<Name>.prompt.md`. Real styles: `styles.css` → `_ds_bundle.css` (tokens on `:root` plus every class above).
