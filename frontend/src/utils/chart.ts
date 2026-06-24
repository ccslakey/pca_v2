import type { ChartSeason, MetricId } from '../types';

// ---- Metric formatting ----

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

// ---- Y-axis tick generation ----

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

// ---- Y-domain padding ----

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

// ---- X-axis tick generation ----

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

// ---- Peak / career aggregates (for player cards) ----

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

export function sumMetric(seasons: ChartSeason[], metric: MetricId): number | null {
  if (['war', 'hr', 'so'].includes(metric)) {
    return seasons.reduce((s, x) => s + ((x[metric as keyof ChartSeason] as number) ?? 0), 0);
  }
  const vals = seasons.map(s => s[metric as keyof ChartSeason]).filter((v): v is number => v != null);
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}
