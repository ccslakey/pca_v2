import { useState, useMemo, useCallback, useEffect } from 'react';
import type { ChartPlayer, MetricId } from '../types';
import { scaleLinear } from '../utils/chart';

interface Props {
  players: ChartPlayer[];
  metric: MetricId;
  yearRange: [number, number];
  fullRange: [number, number];
  setYearRange: (r: [number, number]) => void;
  width: number;
}

interface Drag {
  kind: 'move' | 'l' | 'r';
  startX: number;
  startRange: [number, number];
}

const HEIGHT   = 60;
const MARGIN   = { top: 6, right: 28, bottom: 18, left: 44 };

export function BrushChart({ players, metric, yearRange, fullRange, setYearRange, width }: Props) {
  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, HEIGHT - MARGIN.top - MARGIN.bottom);

  const x = useMemo(() => scaleLinear(fullRange, [0, innerW]), [fullRange, innerW]);

  // Aggregate max value per season for the backdrop sparkline
  const maxVals = useMemo(() => {
    const map = new Map<number, number>();
    players.forEach(p =>
      p.seasons.forEach(s => {
        const v = s[metric];
        if (v == null) return;
        const cur = map.get(s.season);
        const cmp = metric === 'era' ? Math.min : Math.max;
        map.set(s.season, cur == null ? v : cmp(cur, v));
      }),
    );
    return map;
  }, [players, metric]);

  const yD = useMemo(() => {
    const vals = [...maxVals.values()];
    return vals.length ? [Math.min(...vals, 0), Math.max(...vals)] as [number, number] : [0, 1] as [number, number];
  }, [maxVals]);

  const y = useMemo(() => scaleLinear(yD, [innerH, 0]), [yD, innerH]);

  const areaPath = useMemo(() => {
    const seasons = [...maxVals.entries()].sort((a, b) => a[0] - b[0]);
    if (!seasons.length) return '';
    let d = `M ${x(seasons[0][0])} ${innerH}`;
    seasons.forEach(([s, v]) => { d += ` L ${x(s)} ${y(v)}`; });
    d += ` L ${x(seasons[seasons.length - 1][0])} ${innerH} Z`;
    return d;
  }, [maxVals, x, y, innerH]);

  const [drag, setDrag] = useState<Drag | null>(null);

  const onMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!drag) return;
      const dx    = e.clientX - drag.startX;
      const dyears = (dx / innerW) * (fullRange[1] - fullRange[0]);
      let [lo, hi] = drag.startRange;
      if (drag.kind === 'move') {
        lo += dyears; hi += dyears;
        if (lo < fullRange[0]) { hi += fullRange[0] - lo; lo = fullRange[0]; }
        if (hi > fullRange[1]) { lo -= hi - fullRange[1]; hi = fullRange[1]; }
      } else if (drag.kind === 'l') {
        lo = Math.min(hi - 1, Math.max(fullRange[0], lo + dyears));
      } else {
        hi = Math.max(lo + 1, Math.min(fullRange[1], hi + dyears));
      }
      setYearRange([Math.round(lo), Math.round(hi)]);
    },
    [drag, innerW, fullRange, setYearRange],
  );

  useEffect(() => {
    if (!drag) return;
    const onUp = () => setDrag(null);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [drag, onMouseMove]);

  const wx = x(yearRange[0]);
  const ww = Math.max(2, x(yearRange[1]) - x(yearRange[0]));

  return (
    <div className="brush-wrap">
      <svg className="brush-svg" viewBox={`0 0 ${width} ${HEIGHT}`}>
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          <path d={areaPath} fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />

          {/* Mask outside selection */}
          <rect className="brush-mask" x="0" y="0" width={wx} height={innerH} />
          <rect className="brush-mask" x={wx + ww} y="0" width={Math.max(0, innerW - wx - ww)} height={innerH} />

          {/* Brush window */}
          <rect
            className="brush-window"
            x={wx} y="0" width={ww} height={innerH}
            onMouseDown={e => setDrag({ kind: 'move', startX: e.clientX, startRange: [...yearRange] as [number, number] })}
          />
          {/* Handles */}
          <rect
            className="brush-handle"
            x={wx - 3} y={innerH / 2 - 8} width="6" height="16" rx="2"
            onMouseDown={e => { e.stopPropagation(); setDrag({ kind: 'l', startX: e.clientX, startRange: [...yearRange] as [number, number] }); }}
          />
          <rect
            className="brush-handle"
            x={wx + ww - 3} y={innerH / 2 - 8} width="6" height="16" rx="2"
            onMouseDown={e => { e.stopPropagation(); setDrag({ kind: 'r', startX: e.clientX, startRange: [...yearRange] as [number, number] }); }}
          />

          {/* Labels */}
          <text className="brush-label" x={wx}      y={innerH + 14} textAnchor="middle">{yearRange[0]}</text>
          <text className="brush-label" x={wx + ww} y={innerH + 14} textAnchor="middle">{yearRange[1]}</text>
          <text x="-8"         y={innerH / 2} dy="0.32em" textAnchor="end"   className="brush-label" opacity="0.5">{fullRange[0]}</text>
          <text x={innerW + 8} y={innerH / 2} dy="0.32em" textAnchor="start" className="brush-label" opacity="0.5">{fullRange[1]}</text>
        </g>
      </svg>
    </div>
  );
}
