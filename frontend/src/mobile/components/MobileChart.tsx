import { useMemo } from 'react';
import type { ChartPlayer, ChartSeason, MetricId } from '../../types';
import { fmtMetric, isLowerBetter, peakSeason } from '../../utils/chart';

interface Props {
  player: ChartPlayer;
  metric: MetricId;
  color: string;
  width?: number;
  height?: number;
}

const PAD = { top: 22, right: 14, bottom: 22, left: 28 };

/** Single-line career-arc chart (by season). Plain SVG, ported from the comp's
 *  MobileChart.jsx — grid, axes, zero line, gradient area, peak marker. */
export function MobileChart({ player, metric, color, width = 340, height = 180 }: Props) {
  const innerW = width - PAD.left - PAD.right;
  const innerH = height - PAD.top - PAD.bottom;

  const data = useMemo(
    () =>
      player.seasons
        .filter(s => s[metric as keyof ChartSeason] != null)
        .map(s => ({ season: s.season, v: s[metric as keyof ChartSeason] as number })),
    [player.seasons, metric],
  );

  const peak = useMemo(() => peakSeason(player.seasons, metric), [player.seasons, metric]);

  if (!data.length) {
    return <svg className="m-chart" viewBox={`0 0 ${width} ${height}`} />;
  }

  const xs = data.map(d => d.season);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const vs = data.map(d => d.v);
  let v0 = Math.min(...vs);
  let v1 = Math.max(...vs);
  if (metric === 'war') {
    v0 = Math.min(v0, 0);
    v1 = Math.max(v1, 5);
  }
  if (isLowerBetter(metric)) {
    const swap = v0;
    v0 = v1;
    v1 = swap;
  }
  const xSpan = Math.max(1, x1 - x0);
  const vSpan = v1 - v0 || 1;

  const xOf = (s: number) => PAD.left + ((s - x0) / xSpan) * innerW;
  const yOf = (v: number) => PAD.top + (1 - (v - v0) / vSpan) * innerH;

  const path = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'}${xOf(d.season).toFixed(1)} ${yOf(d.v).toFixed(1)}`)
    .join(' ');
  const baseY = PAD.top + innerH;
  const area = `${path} L ${xOf(data[data.length - 1].season).toFixed(1)} ${baseY} L ${xOf(data[0].season).toFixed(1)} ${baseY} Z`;

  const peakX = peak ? xOf(peak.season) : 0;
  const peakY = peak ? yOf(peak.val) : 0;

  const yTicks = Array.from({ length: 4 }, (_, i) => {
    const t = i / 3;
    return { v: v0 + t * vSpan, y: PAD.top + (1 - t) * innerH };
  });

  const xTicks =
    data.length <= 6
      ? data.map(d => ({ s: d.season, x: xOf(d.season) }))
      : [data[0], data[Math.floor(data.length / 2)], data[data.length - 1]].map(d => ({
          s: d.season,
          x: xOf(d.season),
        }));

  return (
    <svg
      className="m-chart"
      viewBox={`0 0 ${width} ${height}`}
      style={{ ['--team-color' as string]: color }}
      role="img"
      aria-label={`${player.name} ${metric} by season`}
    >
      <g className="grid">
        {yTicks.map((t, i) => (
          <line key={i} x1={PAD.left} x2={PAD.left + innerW} y1={t.y} y2={t.y} />
        ))}
      </g>
      <g className="axis">
        {yTicks.map((t, i) => (
          <text key={i} x={PAD.left - 6} y={t.y} textAnchor="end" dominantBaseline="middle">
            {fmtMetric(metric, t.v)}
          </text>
        ))}
        {xTicks.map((t, i) => (
          <text key={i} x={t.x} y={height - 6} textAnchor="middle">
            {String(t.s).slice(2)}
          </text>
        ))}
      </g>
      {metric === 'war' && (
        <line className="chart-zero" x1={PAD.left} x2={PAD.left + innerW} y1={yOf(0)} y2={yOf(0)} />
      )}
      <path className="area" d={area} fill={color} />
      <path className="line" d={path} stroke={color} />
      {peak && (
        <g>
          <circle className="peak-dot" cx={peakX} cy={peakY} r={4.5} />
          <text className="peak-label" x={peakX} y={peakY - 10} textAnchor="middle">
            peak {fmtMetric(metric, peak.val)} · '{String(peak.season).slice(2)}
          </text>
        </g>
      )}
    </svg>
  );
}
