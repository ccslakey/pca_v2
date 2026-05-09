import { useState, useRef, useMemo, useCallback } from 'react';
import type { ChartPlayer, MetricId } from '../types';
import { scaleLinear, smoothPath, fmtMetric, yTicks, yDomain, xTicks } from '../utils/chart';

interface Props {
  players: ChartPlayer[];
  metric: MetricId;
  yearRange: [number, number];
  hoverPlayerId: string | null;
  setHoverPlayerId: (id: string | null) => void;
  width: number;
  height?: number;
}

interface HoverState {
  season: number;
  clientX: number;
  clientY: number;
}

const MARGIN = { top: 18, right: 28, bottom: 30, left: 44 };

export function CareerChart({
  players,
  metric,
  yearRange,
  hoverPlayerId,
  setHoverPlayerId,
  width,
  height = 420,
}: Props) {
  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

  const allVals = useMemo(() => {
    const vals: number[] = [];
    players.forEach(p =>
      p.seasons.forEach(s => {
        if (s.season < yearRange[0] || s.season > yearRange[1]) return;
        const v = s[metric];
        if (v != null) vals.push(v);
      }),
    );
    return vals;
  }, [players, metric, yearRange]);

  const [yLo, yHi] = useMemo(() => yDomain(allVals, metric), [allVals, metric]);
  const x = useMemo(() => scaleLinear(yearRange, [0, innerW]), [yearRange, innerW]);
  const y = useMemo(() => scaleLinear([yLo, yHi], [innerH, 0]), [yLo, yHi, innerH]);

  const yt = useMemo(() => yTicks(yLo, yHi, metric), [yLo, yHi, metric]);
  const xt = useMemo(() => xTicks(yearRange[0], yearRange[1]), [yearRange]);

  const [hover, setHover] = useState<HoverState | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const onMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const rect = svgRef.current?.getBoundingClientRect();
      if (!rect) return;
      const px = e.clientX - rect.left - MARGIN.left;
      if (px < 0 || px > innerW) { setHover(null); return; }
      const season = Math.round(x.invert(px));
      if (season < yearRange[0] || season > yearRange[1]) { setHover(null); return; }
      setHover({ season, clientX: e.clientX - rect.left, clientY: e.clientY - rect.top });
    },
    [x, innerW, yearRange],
  );

  const lineData = useMemo(
    () =>
      players.map(p => {
        const pts = p.seasons
          .filter(s => s.season >= yearRange[0] && s.season <= yearRange[1] && s[metric] != null)
          .map(s => ({ season: s.season, val: s[metric] as number }));
        const coords: [number, number][] = pts.map(pt => [x(pt.season), y(pt.val)]);
        return { player: p, pts, path: smoothPath(coords) };
      }),
    [players, metric, yearRange, x, y],
  );

  const tooltip = useMemo(() => {
    if (!hover) return null;
    const rows = lineData
      .map(({ player, pts }) => {
        const pt = pts.find(p => p.season === hover.season);
        return pt ? { player, val: pt.val } : null;
      })
      .filter(Boolean) as { player: ChartPlayer; val: number }[];
    return { season: hover.season, rows, x: hover.clientX, y: hover.clientY };
  }, [hover, lineData]);

  return (
    <div style={{ position: 'relative' }}>
      <svg
        ref={svgRef}
        className="chart"
        viewBox={`0 0 ${width} ${height}`}
        onMouseMove={onMouseMove}
        onMouseLeave={() => setHover(null)}
      >
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {/* Grid */}
          <g className="grid">
            {yt.map((t, i) => (
              <line key={i} x1="0" x2={innerW} y1={y(t)} y2={y(t)} />
            ))}
          </g>

          {/* Zero line */}
          {metric === 'war' && yLo < 0 && (
            <line className="chart-zero" x1="0" x2={innerW} y1={y(0)} y2={y(0)} />
          )}

          {/* Y axis */}
          <g className="axis">
            {yt.map((t, i) => (
              <text key={i} x="-10" y={y(t)} dy="0.32em" textAnchor="end">
                {fmtMetric(metric, t)}
              </text>
            ))}
          </g>

          {/* X axis */}
          <g className="axis" transform={`translate(0,${innerH})`}>
            <line x1="0" x2={innerW} />
            {xt.map((t, i) => (
              <text key={i} x={x(t)} y="20" textAnchor="middle">{t}</text>
            ))}
          </g>

          {/* Crosshair */}
          {hover && (
            <line
              className="crosshair"
              x1={x(hover.season)} x2={x(hover.season)}
              y1={0} y2={innerH}
            />
          )}

          {/* Lines */}
          {lineData.map(({ player, path }) => {
            const dim = hoverPlayerId !== null && hoverPlayerId !== player.id;
            const hov = hoverPlayerId === player.id;
            return (
              <path
                key={player.id}
                d={path}
                className={`line ${dim ? 'is-dim' : ''} ${hov ? 'is-hover' : ''}`}
                stroke={player.color}
                onMouseEnter={() => setHoverPlayerId(player.id)}
                onMouseLeave={() => setHoverPlayerId(null)}
              />
            );
          })}

          {/* Dots */}
          {lineData.map(({ player, pts }) =>
            pts.map(pt => {
              const isHoverSeason = hover?.season === pt.season;
              const dim = hoverPlayerId !== null && hoverPlayerId !== player.id;
              return (
                <circle
                  key={`${player.id}-${pt.season}`}
                  className="dot"
                  cx={x(pt.season)}
                  cy={y(pt.val)}
                  r={isHoverSeason ? 4.5 : 2.2}
                  fill={player.color}
                  stroke="#0f1117"
                  strokeWidth="1.5"
                  opacity={dim ? 0.2 : 1}
                />
              );
            }),
          )}
        </g>
      </svg>

      {tooltip && tooltip.rows.length > 0 && (
        <div className="tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          <div className="tooltip-season">{tooltip.season}</div>
          {tooltip.rows
            .sort((a, b) => (metric === 'era' ? a.val - b.val : b.val - a.val))
            .map(r => (
              <div key={r.player.id} className="tooltip-row">
                <span className="l">
                  <span className="swatch" style={{ background: r.player.color }} />
                  {r.player.name}
                </span>
                <span className="v">{fmtMetric(metric, r.val)}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
