import { useMemo } from 'react';
import type { ChartPlayer, ChartSeason, MetricId } from '../../types';
import { fmtMetric, isLowerBetter } from '../../utils/chart';

interface Props {
  players: ChartPlayer[];
  metric: MetricId;
  focusId?: string | null;
  height?: number;
}

const PAD = { t: 18, r: 12, b: 22, l: 26 };

/** Overlaid multi-line career-arc chart aligned by AGE. Ported from the comp's
 *  MobileMultiChart (overlay mode): grid, axes, zero line, dim/focus lines, and
 *  a gradient area + peak marker on the focused line. */
export function MobileMultiChart({ players, metric, focusId, height = 188 }: Props) {
  const W = 320;
  const H = height;
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;

  const series = useMemo(
    () =>
      players
        .map(p => ({
          id: p.id,
          color: p.color,
          pts: p.seasons
            .filter(s => s.age != null && s[metric as keyof ChartSeason] != null)
            .map(s => ({ x: s.age as number, v: s[metric as keyof ChartSeason] as number })),
        }))
        .filter(s => s.pts.length),
    [players, metric],
  );

  if (!series.length) return <svg className="m-multichart" viewBox={`0 0 ${W} ${H}`} />;

  const allX = series.flatMap(s => s.pts.map(p => p.x));
  const allV = series.flatMap(s => s.pts.map(p => p.v));
  const x0 = Math.min(...allX);
  const x1 = Math.max(...allX);
  let lo = Math.min(...allV);
  const hi = Math.max(...allV);
  if (['war', 'hr', 'so'].includes(metric)) lo = Math.min(lo, 0);
  const invert = isLowerBetter(metric);
  const xSpan = x1 - x0 || 1;
  const vSpan = hi - lo || 1;

  const xOf = (x: number) => PAD.l + ((x - x0) / xSpan) * iw;
  const yOf = (v: number) => {
    let t = (v - lo) / vSpan;
    if (invert) t = 1 - t;
    return PAD.t + (1 - t) * ih;
  };

  const yTicks = Array.from({ length: 4 }, (_, i) => ({
    v: lo + (i / 3) * vSpan,
    y: PAD.t + (1 - i / 3) * ih,
  }));
  const xStep = Math.max(2, Math.round(xSpan / 4));
  const xTicks: number[] = [];
  for (let a = x0; a <= x1 + 0.1; a += xStep) xTicks.push(Math.round(a));

  const pathOf = (pts: { x: number; v: number }[]) =>
    pts.map((p, i) => `${i ? 'L' : 'M'}${xOf(p.x).toFixed(1)} ${yOf(p.v).toFixed(1)}`).join(' ');

  const focusSeries = focusId ? series.find(s => s.id === focusId) : null;
  const peak = focusSeries
    ? focusSeries.pts.reduce((a, b) => (invert ? (b.v < a.v ? b : a) : b.v > a.v ? b : a))
    : null;

  return (
    <svg className="m-multichart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Comparison of ${metric} by age`}>
      <g className="grid">
        {yTicks.map((t, i) => (
          <line key={i} x1={PAD.l} x2={PAD.l + iw} y1={t.y} y2={t.y} />
        ))}
      </g>
      <g className="axis">
        {yTicks.map((t, i) => (
          <text key={i} x={PAD.l - 6} y={t.y + 3} textAnchor="end">
            {fmtMetric(metric, t.v)}
          </text>
        ))}
        {xTicks.map((a, i) => (
          <text key={i} x={xOf(a)} y={H - 7} textAnchor="middle">
            {a}
          </text>
        ))}
      </g>
      {metric === 'war' && lo < 0 && (
        <line className="zero" x1={PAD.l} x2={PAD.l + iw} y1={yOf(0)} y2={yOf(0)} />
      )}
      {/* area under the focused line only */}
      {focusSeries && (
        <path
          className="area"
          d={`${pathOf(focusSeries.pts)} L ${xOf(focusSeries.pts[focusSeries.pts.length - 1].x).toFixed(1)} ${PAD.t + ih} L ${xOf(focusSeries.pts[0].x).toFixed(1)} ${PAD.t + ih} Z`}
          fill={focusSeries.color}
        />
      )}
      {/* lines */}
      {series.map(s => {
        const isFocus = focusId === s.id;
        const dim = focusId && !isFocus;
        return (
          <path
            key={s.id}
            className={`ln${dim ? ' is-dim' : isFocus ? ' is-focus' : ''}`}
            d={pathOf(s.pts)}
            stroke={s.color}
          />
        );
      })}
      {/* peak marker on focused line */}
      {focusSeries && peak && (
        <g>
          <circle cx={xOf(peak.x)} cy={yOf(peak.v)} r={4} fill={focusSeries.color} stroke="var(--bg-2)" strokeWidth={2} />
          <text
            x={xOf(peak.x)}
            y={yOf(peak.v) - 9}
            textAnchor="middle"
            fontFamily="var(--font-mono)"
            fontSize={9.5}
            fill="var(--text-1)"
          >
            {fmtMetric(metric, peak.v)}
          </text>
        </g>
      )}
    </svg>
  );
}
