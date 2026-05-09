import type { ChartSeason, MetricId } from '../types';

// ---- Linear scale ----

export interface Scale {
  (v: number): number;
  invert(p: number): number;
  domain(): [number, number];
  range(): [number, number];
}

export function scaleLinear(domain: [number, number], range: [number, number]): Scale {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  const fn = (v: number) => r0 + ((v - d0) / span) * (r1 - r0);
  fn.invert = (p: number) => d0 + ((p - r0) / (r1 - r0)) * span;
  fn.domain = () => domain;
  fn.range  = () => range;
  return fn as Scale;
}

// ---- Catmull-Rom → cubic Bezier path ----

type Point = [number, number];

export function smoothPath(points: Point[]): string {
  if (!points.length) return '';
  if (points.length === 1) return `M ${points[0][0]} ${points[0][1]}`;
  let d = `M ${points[0][0]} ${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C ${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${p2[0].toFixed(2)} ${p2[1].toFixed(2)}`;
  }
  return d;
}

// ---- Metric formatting ----

export function fmtMetric(metric: MetricId, v: number | null): string {
  if (v == null || isNaN(v)) return '—';
  if (metric === 'avg') return v.toFixed(3).replace(/^0\./, '.');
  if (metric === 'ops') return v.toFixed(3).replace(/^0\./, '.');
  if (metric === 'war') return v.toFixed(1);
  if (metric === 'era') return v.toFixed(2);
  return Math.round(v).toString();
}

// ---- Y-axis tick generation ----

export function yTicks(lo: number, hi: number, metric: MetricId): number[] {
  const span = hi - lo;
  let step: number;
  if (metric === 'avg' || metric === 'ops') step = span > 0.2 ? 0.05 : 0.02;
  else if (metric === 'era') step = 1;
  else if (metric === 'war') step = 2;
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
  } else {
    lo = Math.min(0, lo);
    hi = hi + (hi - lo) * 0.1;
  }
  return [lo, hi];
}

// ---- X-axis tick generation ----

export function xTicks(lo: number, hi: number): number[] {
  const span = hi - lo;
  const step = span > 16 ? 4 : span > 8 ? 2 : 1;
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
  pts.sort(metric === 'era' ? (a, b) => a.val - b.val : (a, b) => b.val - a.val);
  return pts[0];
}

export function careerWar(seasons: { war: number | null }[]): number {
  return Math.round(seasons.reduce((sum, s) => sum + (s.war ?? 0), 0) * 10) / 10;
}
