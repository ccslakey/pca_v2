import { useMemo } from 'react';
import type { ChartPlayer, ChartSeason, MetricId, XMode } from '../../types';
import { isLowerBetter, yDomain } from '../../utils/chart';

interface Props {
  players: ChartPlayer[];
  metric: MetricId;
  xMode?: XMode;
  height?: number;
  highlightId?: string | null;
}

const PAD = { top: 14, right: 12, bottom: 22, left: 30 };

function xOf(s: ChartSeason, xMode: XMode): number | null {
  return xMode === 'age' ? s.age : s.season;
}

/** Overlaid multi-line career chart for the Compare overlay layout. Plain SVG. */
export function MobileMultiChart({ players, metric, xMode = 'age', height = 240, highlightId }: Props) {
  const width = 360;

  const series = useMemo(() => {
    return players.map(p => ({
      id: p.id,
      color: p.color,
      pts: p.seasons
        .map(s => ({ x: xOf(s, xMode), y: s[metric as keyof ChartSeason] as number | null }))
        .filter((q): q is { x: number; y: number } => q.x != null && q.y != null),
    }));
  }, [players, metric, xMode]);

  const allPts = series.flatMap(s => s.pts);
  if (allPts.length === 0) {
    return <div className="m-chart-empty" style={{ height }}>No {metric.toUpperCase()} data</div>;
  }

  const xs = allPts.map(p => p.x);
  const [xLo, xHi] = [Math.min(...xs), Math.max(...xs)];
  const [yLo, yHi] = yDomain(allPts.map(p => p.y), metric);

  const iw = width - PAD.left - PAD.right;
  const ih = height - PAD.top - PAD.bottom;

  const sx = (x: number) => PAD.left + (xHi === xLo ? iw / 2 : ((x - xLo) / (xHi - xLo)) * iw);
  const sy = (y: number) => PAD.top + (yHi === yLo ? ih / 2 : (1 - (y - yLo) / (yHi - yLo)) * ih);

  const topVal = isLowerBetter(metric) ? yLo : yHi;
  const botVal = isLowerBetter(metric) ? yHi : yLo;

  return (
    <svg
      className="m-chart"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={`Comparison of ${metric} by ${xMode}`}
    >
      <line
        x1={PAD.left} x2={width - PAD.right}
        y1={PAD.top + ih} y2={PAD.top + ih}
        stroke="var(--line)" strokeWidth={1}
      />

      {series.map(s => {
        if (s.pts.length === 0) return null;
        const dimmed = highlightId != null && highlightId !== s.id;
        const line = s.pts
          .map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`)
          .join(' ');
        return (
          <path
            key={s.id}
            d={line}
            fill="none"
            stroke={s.color}
            strokeWidth={highlightId === s.id ? 2.6 : 2}
            strokeOpacity={dimmed ? 0.25 : 1}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        );
      })}

      <text x={4} y={PAD.top + 4} className="m-chart-axis" fill="var(--text-3)">{fmt(topVal)}</text>
      <text x={4} y={PAD.top + ih} className="m-chart-axis" fill="var(--text-3)">{fmt(botVal)}</text>
      <text x={PAD.left} y={height - 6} className="m-chart-axis" fill="var(--text-3)">{xLo}</text>
      <text x={width - PAD.right} y={height - 6} textAnchor="end" className="m-chart-axis" fill="var(--text-3)">{xHi}</text>
    </svg>
  );
}

function fmt(v: number): string {
  if (Math.abs(v) >= 100) return Math.round(v).toString();
  if (Math.abs(v) < 10 && !Number.isInteger(v)) return v.toFixed(1);
  return Math.round(v).toString();
}
