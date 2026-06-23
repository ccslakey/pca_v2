import { useMemo } from 'react';
import type { ChartPlayer, ChartSeason, MetricId, XMode } from '../../types';
import { fmtMetric, isLowerBetter, peakSeason, yDomain } from '../../utils/chart';

interface Props {
  player: ChartPlayer;
  metric: MetricId;
  color: string;
  xMode?: XMode;
  height?: number;
}

const PAD = { top: 14, right: 14, bottom: 22, left: 30 };

function xOf(s: ChartSeason, xMode: XMode): number | null {
  return xMode === 'age' ? s.age : s.season;
}

/** Single-line career chart for one player + metric. Plain SVG (no visx). */
export function MobileChart({ player, metric, color, xMode = 'year', height = 200 }: Props) {
  const width = 360; // viewBox units; SVG scales to container width

  const pts = useMemo(() => {
    return player.seasons
      .map(s => ({ x: xOf(s, xMode), y: s[metric as keyof ChartSeason] as number | null }))
      .filter((p): p is { x: number; y: number } => p.x != null && p.y != null);
  }, [player.seasons, metric, xMode]);

  const peak = useMemo(() => peakSeason(player.seasons, metric), [player.seasons, metric]);

  if (pts.length === 0) {
    return (
      <div className="m-chart-empty" style={{ height }}>
        No {metric.toUpperCase()} data
      </div>
    );
  }

  const xs = pts.map(p => p.x);
  const [xLo, xHi] = [Math.min(...xs), Math.max(...xs)];
  const [yLo, yHi] = yDomain(pts.map(p => p.y), metric);

  const iw = width - PAD.left - PAD.right;
  const ih = height - PAD.top - PAD.bottom;

  const sx = (x: number) => PAD.left + (xHi === xLo ? iw / 2 : ((x - xLo) / (xHi - xLo)) * iw);
  const sy = (y: number) => PAD.top + (yHi === yLo ? ih / 2 : (1 - (y - yLo) / (yHi - yLo)) * ih);

  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ');
  const area = `${line} L${sx(pts[pts.length - 1].x).toFixed(1)},${(PAD.top + ih).toFixed(1)} L${sx(pts[0].x).toFixed(1)},${(PAD.top + ih).toFixed(1)} Z`;

  const gradId = `mc-${player.id}-${metric}`.replace(/[^a-z0-9-]/gi, '');
  const peakX = peak != null && xMode === 'year' ? sx(peak.season) : null;

  // Two y-axis labels (lo / hi) and the value extremes.
  const yLabel = isLowerBetter(metric)
    ? { topVal: yLo, botVal: yHi }
    : { topVal: yHi, botVal: yLo };

  return (
    <svg
      className="m-chart"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={`${player.name} ${metric} by ${xMode}`}
    >
      <defs>
        <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.22} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>

      {/* baseline */}
      <line
        x1={PAD.left} x2={width - PAD.right}
        y1={PAD.top + ih} y2={PAD.top + ih}
        stroke="var(--line)" strokeWidth={1}
      />

      <path d={area} fill={`url(#${gradId})`} />
      <path d={line} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

      {pts.map((p, i) => (
        <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={1.6} fill={color} />
      ))}

      {peakX != null && peak != null && (
        <>
          <circle cx={peakX} cy={sy(peak.val)} r={3.5} fill={color} stroke="var(--bg-1)" strokeWidth={1.5} />
        </>
      )}

      {/* y extremes */}
      <text x={4} y={PAD.top + 4} className="m-chart-axis" fill="var(--text-3)">
        {fmtMetric(metric, yLabel.topVal)}
      </text>
      <text x={4} y={PAD.top + ih} className="m-chart-axis" fill="var(--text-3)">
        {fmtMetric(metric, yLabel.botVal)}
      </text>

      {/* x extremes */}
      <text x={PAD.left} y={height - 6} className="m-chart-axis" fill="var(--text-3)">
        {xLo}
      </text>
      <text x={width - PAD.right} y={height - 6} textAnchor="end" className="m-chart-axis" fill="var(--text-3)">
        {xHi}
      </text>
    </svg>
  );
}
