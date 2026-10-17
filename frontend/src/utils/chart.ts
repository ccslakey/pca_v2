import type { ChartSeason, MetricId } from '../types';

export function fmtMetric(metric: MetricId, v: number | null): string {
  if (v == null || isNaN(v)) return '—';
  if (metric === 'avg') return v.toFixed(3).replace(/^0\./, '.');
  if (metric === 'ops') return v.toFixed(3).replace(/^0\./, '.');
  if (metric === 'war') return v.toFixed(1);
  if (metric === 'era') return v.toFixed(2);
  return Math.round(v).toString();
}

export function isLowerBetter(metric: MetricId): boolean {
  return metric === 'era';
}

export function yTicks(lo: number, hi: number, metric: MetricId): number[] {
  const span = hi - lo;
  let step: number;
  if (metric === 'avg' || metric === 'ops') step = span > 0.2 ? 0.05 : 0.02;
  else if (metric === 'era') step = 1;
  else if (metric === 'war') step = 2;
  else if (metric === 'ops_plus' || metric === 'era_plus') step = span > 100 ? 50 : 25;
  else step = Math.pow(10, Math.floor(Math.log10(span / 5)));
  const ticks: number[] = [];
  const start = Math.ceil(lo / step) * step;
  for (let v = start; v <= hi + 1e-9; v += step) ticks.push(+v.toFixed(4));
  return ticks;
}

export function yDomain(vals: number[], metric: MetricId): [number, number] {
  if (!vals.length) return [0, 10];
  let lo = Math.min(...vals);
  let hi = Math.max(...vals);
  if (metric === 'era') {
    lo = Math.max(0, lo - 0.5);
    hi = hi + 0.5;
  } else if (metric === 'avg' || metric === 'ops') {
    lo = Math.max(0, lo - 0.02);
    hi = hi + 0.02;
  } else if (metric === 'ops_plus' || metric === 'era_plus') {
    lo = lo - 15;
    hi = hi + 15;
  } else {
    lo = Math.min(0, lo);
    hi = hi + (hi - lo) * 0.1;
  }
  return [lo, hi];
}

export function xTicks(lo: number, hi: number, innerWidth?: number): number[] {
  const span = hi - lo;
  let step = span > 16 ? 4 : span > 8 ? 2 : 1;
  if (innerWidth) {
    // A 4-digit year label needs ~48px to stay legible; widen the step on
    // narrow charts until the ticks fit.
    const maxTicks = Math.max(2, Math.floor(innerWidth / 48));
    for (const s of [step, 2, 4, 5, 10, 20, 25, 50]) {
      step = Math.max(step, s);
      if (span / step <= maxTicks) break;
    }
  }
  const ticks: number[] = [];
  const start = Math.ceil(lo / step) * step;
  for (let v = start; v <= hi; v += step) ticks.push(v);
  return ticks;
}

type StatKey = Exclude<MetricId, never>;

export function peakSeason(
  seasons: ChartSeason[],
  metric: MetricId,
): { season: number; val: number } | null {
  const key = metric as StatKey & keyof ChartSeason;
  const pts = seasons
    .filter(s => s[key] != null)
    .map(s => ({ season: s.season, val: s[key] as number }));
  if (!pts.length) return null;
  pts.sort(isLowerBetter(metric) ? (a, b) => a.val - b.val : (a, b) => b.val - a.val);
  return pts[0];
}

export function careerWar(seasons: { war: number | null }[]): number {
  return Math.round(seasons.reduce((sum, s) => sum + (s.war ?? 0), 0) * 10) / 10;
}

type TotalKey = 'pa' | 'ab' | 'h' | 'ip_outs' | 'er';

/** Sum of a season total, or null when any season lacks it (no totals to use). */
function seasonTotal(seasons: ChartSeason[], key: TotalKey): number | null {
  if (!seasons.every(s => s[key] != null)) return null;
  return seasons.reduce((n, s) => n + (s[key] ?? 0), 0);
}

function weightedMean(seasons: ChartSeason[], metric: MetricId, weight: TotalKey): number | null {
  let num = 0;
  let den = 0;
  for (const s of seasons) {
    const v = s[metric as keyof ChartSeason] as number | null;
    const w = s[weight] ?? 0;
    if (v == null || w <= 0) continue;
    num += v * w;
    den += w;
  }
  return den > 0 ? num / den : null;
}

/**
 * Career value of a metric. Counting stats are summed. Rate stats come from
 * season totals, matching the backend (players/narrative.py), so a 6-inning
 * season can't swing a career ERA:
 *   AVG  = ΣH / ΣAB
 *   ERA  = 27·ΣER / Σouts
 *   ERA+ = earned-run-weighted mean of season ERA+ (exact, since ERA+ = 100·lgERA/ERA)
 *   OPS, OPS+ = PA-weighted mean of season values (close, not exact)
 * Seasons without totals fall back to a plain mean of the season values.
 */
export function sumMetric(seasons: ChartSeason[], metric: MetricId): number | null {
  if (['war', 'hr', 'so'].includes(metric)) {
    return seasons.reduce((s, x) => s + ((x[metric as keyof ChartSeason] as number) ?? 0), 0);
  }
  if (metric === 'avg') {
    const ab = seasonTotal(seasons, 'ab');
    const h = seasonTotal(seasons, 'h');
    if (ab != null && h != null) return ab > 0 ? h / ab : null;
  }
  if (metric === 'era') {
    const outs = seasonTotal(seasons, 'ip_outs');
    const er = seasonTotal(seasons, 'er');
    if (outs != null && er != null) return outs > 0 ? (27 * er) / outs : null;
  }
  const weight: TotalKey | null =
    metric === 'era_plus' ? 'er' : metric === 'ops' || metric === 'ops_plus' ? 'pa' : null;
  if (weight && seasonTotal(seasons, weight) != null) return weightedMean(seasons, metric, weight);

  const vals = seasons.map(s => s[metric as keyof ChartSeason]).filter((v): v is number => v != null);
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}
