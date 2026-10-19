# Design-sync notes (PCA frontend → claude.ai/design)

Project: https://claude.ai/design/p/3340e21a-8206-4065-bbb4-9aef7abd0345 ("PCA Design System"). Run everything from `frontend/`.

## How this repo is built for the sync

- This is an app (Vite SPA), not a published library. `.design-sync/build-ds.mjs` (`cfg.buildCmd`) is the library build:
  - Vite library mode compiles `.design-sync/ds-entry.tsx` (a barrel re-exporting app components) plus all SCSS into `ds-dist/index.js` and `ds-dist/style.css`.
  - `tsc -p .design-sync/tsconfig.ds.json` emits `.d.ts` into `ds-dist/types/`.
  - The script writes `ds-dist/package.json`. `ds-dist/` is gitignored.
- The converter gets `--entry ./ds-dist/index.js`, so `ds-dist/` is the package dir. That's why `cfg.srcDir` is `../src` and `cfg.cssEntry` is `style.css`.
- Never set `"type": "module"` in `ds-dist/package.json`. It switches esbuild to Node CJS interop, and `@visx/brush/lib/Brush`'s default import becomes the exports object ("Element type is invalid" in `BrushChart`).
- Vite runs with `envPrefix: '__DS_SYNC_NO_ENV__'` so `.env.local` values (e.g. `VITE_SENTRY_DSN`) can't be inlined into the uploaded bundle. `treeshake.moduleSideEffects` drops unused externals, which keeps Sentry and PostHog out.
- Google Fonts come from `.design-sync/fonts.css`, which uses the same URL as `index.html` and is imported first so the `@import` stays at the top of the CSS.
- Faithful install is `npm ci`. npm 11 blocks install scripts (esbuild postinstall); esbuild works without it.

## Scope decisions (made with the user, 2026-10-14)

- **Exported:** 26 presentational components, plus `AppProviders` (glue in `ds-entry.tsx`: `QueryClientProvider` + `MemoryRouter` + `ThemeProvider`, mirroring `main.tsx`/`App.tsx`), `ThemeProvider`, `useTheme`, `THEMES`, `METRICS`, `PLAYER_COLORS`, `MAX_PLAYERS`, and the pure helpers `peakSeason`, `careerWar`, `sumMetric`, `fmtMetric`, `playerColor`, `colorTint`.
- **No cards for** `AppProviders` and `ThemeProvider` (`componentSrcMap: null`). They're still exported.
- **Excluded because they need the live `/api`:** pages, mobile screens, `MobileApp`, `PlayerSearch`, `TopBar`, `FeaturedGallery`, `PlayerBrowser`, `ChartArea`, `PitchZone`, `NarrativePanel`, `MetricExplainer` (it's still bundled inside `MetricToggle`, which is why the provider needs a QueryClient).
- **Rich previews:** the 20 core components, plus `MobileChart`, `MobileMultiChart` and `SeasonSheet`. Without data those three rendered blank or broken.
- **Placeholder cards (render fine with no props):** `ChartSkeleton`, `ProfilePageSkeleton`, `MobileTabBar`.
- `@phosphor-icons/react` is not exposed as an extra entry. The full icon set would add megabytes; only the icons the components use are bundled.

## Preview fixtures

- `.design-sync/previews/_data.json` holds real data for Trout, Judge, Griffey, Kershaw, Maddux, Ohtani, Trout's similar players, and the batter aging curve. It was exported from the local API by `.design-sync/fixtures/export.ts` (instructions in its header; needs local Postgres + `runserver 127.0.0.1:8765`).
- `_players.ts` wraps the data and mirrors `ComparePage`'s `fullRange`.
- Compare-style previews color players `var(--chart-N)` by slot. Profile-style previews use `playerColor(id)`, as the app does.

## Preview gotchas

- **Sizes and capture viewport:**
  - Per-story capture is 900px wide, so wide components use fluid wrappers (`width: '100%'`).
  - `MetricToggle` has a `1280x400` column viewport because its desktop layout needs about 1100px.
  - `MonthlyHeatmap` has `min-width: 600px`, so its panel is 660px.
- **Layout dependencies:**
  - `SeasonSheet` is `position: absolute` and needs a positioned phone-height parent (`.m-app` with fixed height).
  - `ThemePicker`'s open state is shown by clicking `.tp-trigger` on mount. Its wrapper needs `alignItems: flex-start`, or the menu drops to the bottom of the stretched cell.
- **`BrushChart`:** the brush always starts at `fullRange`, and `xRange` only moves the labels. So it's previewed composed under `CareerChart` with shared range state, as in `ChartArea`.
- **Config changes:**
  - A changed `viewport` override needs a full `package-build.mjs` (`[CONFIG_STALE]`).
  - `cardMode`/`primaryStory` changes are presentation-only and fine with `preview-rebuild.mjs`.

## Known render warns

- `[RENDER_THIN] Sparkline`: benign. Visx `ParentSize` measures 0 on the first frame; the review sheet shows the line drawn.
- `[FONT_REMOTE] Inter, JetBrains Mono`: expected. Theme fonts (Geist, IBM Plex, Cormorant, etc.) are set at runtime by `applyTheme` and served by the same Google Fonts import.
- `tokens: 3 missing, below threshold`: `--team-color`/`--team-tint`/`--team-glow` are set inline by the mobile profile screen, not on `:root`.

## App findings surfaced by the sync (fixed in src/ 2026-10-14)

- `PlayerCard` initials now pick black or white from the slot color's lightness (CSS relative color). Previously they were hard-coded dark, which was invisible on Fangraphs Light `--chart-2` and the darker light-theme palettes.
- `MetricToggle` legend glyphs, which were hard-coded `#f5f7fb`, now use `--text-1`. The `BrushChart` area, which was hard-coded white, is now tinted from `--text-0`.
- `sumMetric` computes career rates from season totals (`pa`/`ab`/`h`/`ip_outs`/`er` on `ChartSeason`), matching the backend. Ohtani's career ERA is 2.86, not 7.66.
- `playerRoles()`: primary pitchers aren't batters, and position players need 100 IP to count as pitchers.
- Still true: `MonthlyHeatmap` simulates monthly values from season OPS.
- Fixtures regenerated 2026-10-18 after these fixes: seasons carry totals, Kershaw/Maddux are pitcher-only, career ERAs read 2.53 (Kershaw) / 2.86 (Ohtani).

## App findings from the 2026-10-18 resync (fixed in src/ the same day)

- `StatGrid` below `$bp-lg` is now a wrapping flex row (headline on its own row, the rest grow to fill), so no block count leaves a gap. The previews capture at 900px, which is this tablet layout.
- `initials()` skips Jr./Sr./II-IV, so "Ken Griffey Jr." is "KG". `PlayerBrowser` and `FeaturedGallery` now use it instead of their own first-letter copies.
- `BrushChart`'s right end label no longer clips: `.brush-svg` is `overflow: visible`, because its 28px right margin is shared with `CareerChart` to keep the axes aligned.

## Re-sync risks

- `_data.json` is a snapshot (2026-10-18). Active players' seasons will drift; regenerate with `fixtures/export.ts` when previews should look current. Edits to `_data.json` / `_players.ts` do NOT re-key grades (only `<Name>.tsx` does). After regenerating, recapture every data-driven preview: `package-capture.mjs --components <upload.components> --spot-check-components <same>`, then read each sheet. The exporter only hits bundle/similar/aging_curve/james endpoints, so a pending `stats` migration doesn't block it.
- Removed props linger in previews and conventions examples because esbuild doesn't type-check. Run `npx tsc --noEmit -p .design-sync/previews` (uses `previews/tsconfig.json`, which maps `pca-design-system` to `ds-dist/`) after rebuilding `ds-dist`.
- `ds-entry.tsx` re-exports components by path. A moved or renamed component fails `build-ds.mjs`; update the barrel.
- The `.d.ts` files reference app types (`ChartPlayer` etc.) by name only. `conventions.md` documents those shapes, so keep it in sync when `src/types.ts` changes.
- Toolchain at sync time: node 26.7, vite 6.4.2, sass 1.99, typescript 5.9.3, playwright 1.62.1 (pinned to the cached chromium-1234).
