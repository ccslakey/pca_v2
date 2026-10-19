// Shared preview fixtures: real player data exported from the local API by
// .design-sync/fixtures/export.ts, in the app's ChartPlayer shape.
import type { ChartPlayer } from 'pca-design-system';
import data from './_data.json';

export const players = data.players as unknown as Record<string, ChartPlayer>;
export const trout = players.troutmi01;
export const judge = players.judgeaa01;
export const griffey = players.griffke02;
export const kershaw = players.kershcl01;
export const maddux = players.maddugr01;
export const ohtani = players.ohtansh01;

export const james = data.james as Record<string, {
  black_ink_bat: number; gray_ink_bat: number; hof_monitor_bat: number;
  black_ink_pit: number; gray_ink_pit: number; hof_monitor_pit: number;
}>;
export const similarToTrout = data.similar.troutmi01;
export const agingBatters = data.agingBatters;

export const noop = () => {};

// ComparePage's fullRange: min/max season (or age) across the selected players.
export function fullRange(ps: ChartPlayer[], xMode: 'year' | 'age'): [number, number] {
  let lo = Infinity, hi = -Infinity;
  for (const p of ps) for (const s of p.seasons) {
    const v = xMode === 'age' ? s.age : s.season;
    if (v == null) continue;
    lo = Math.min(lo, v); hi = Math.max(hi, v);
  }
  return [lo, hi];
}
