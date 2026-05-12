import { useMemo } from 'react';
import { scaleLinear } from '@visx/scale';
import { LinePath } from '@visx/shape';
import { Group } from '@visx/group';
import { GridRows } from '@visx/grid';
import { AxisLeft, AxisBottom } from '@visx/axis';
import { useTooltip, TooltipWithBounds } from '@visx/tooltip';
import { localPoint } from '@visx/event';
import { curveCatmullRom } from 'd3-shape';
import type { AwardKind, ChartPlayer, MetricId, PlayerAward } from '../../types';
import { fmtMetric, yTicks, yDomain, xTicks } from '../../utils/chart';
import { AnnotationGlyph } from '../AnnotationGlyph';

// Awards shown as circled glyphs on the chart line (must be pure SVG — no nested <svg>)
const CHART_KINDS = new Set<AwardKind>(['mvp', 'cy', 'gg', 'asg']);

const AWARD_PRIORITY: Partial<Record<AwardKind, number>> = {
  mvp: 0, cy: 1, gg: 2, asg: 3,
};

const AWARD_LABELS: Partial<Record<AwardKind, string>> = {
  mvp: 'MVP', cy: 'Cy Young', gg: 'Gold Glove', asg: 'All-Star',
  roty: 'Rookie of Year', ws: 'World Series', hof: 'Hall of Fame',
  ss: 'Silver Slugger', tc_b: 'Triple Crown', tc_p: 'Triple Crown',
  bat_title: 'Batting Title', era_title: 'ERA Title',
  all_mlb: 'All-MLB Team', postmvp: 'Postseason MVP',
};

/** Top-priority chart annotation for a player in a given year, null if none. */
function topAnnotation(awards: PlayerAward[], year: number): PlayerAward | null {
  let best: PlayerAward | null = null;
  for (const a of awards) {
    if (a.year !== year || !CHART_KINDS.has(a.kind)) continue;
    if (best === null || (AWARD_PRIORITY[a.kind] ?? 99) < (AWARD_PRIORITY[best.kind] ?? 99)) {
      best = a;
    }
  }
  return best;
}

function ChartGlyph({ kind, color, cx, cy }: { kind: AwardKind; color: string; cx: number; cy: number }) {
  const R = 11;
  const S = R * 1.25;
  return (
    <g pointerEvents="none">
      <circle cx={cx} cy={cy} r={R} fill="var(--bg-1)" stroke={color} strokeWidth={1.5} />
      <svg x={cx - S / 2} y={cy - S / 2} width={S} height={S} overflow="visible">
        <AnnotationGlyph kind={kind} color={color} size={S} />
      </svg>
    </g>
  );
}

interface Props {
  players: ChartPlayer[];
  metric: MetricId;
  yearRange: [number, number];
  hoverPlayerId: string | null;
  setHoverPlayerId: (id: string | null) => void;
  width: number;
  height?: number;
}

interface TooltipData {
  season: number;
  rows: { player: ChartPlayer; val: number }[];
  awardRows: { player: ChartPlayer; award: PlayerAward }[];
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

  const xScale = useMemo(
    () => scaleLinear({ domain: yearRange, range: [0, innerW] }),
    [yearRange, innerW],
  );
  const yScale = useMemo(
    () => scaleLinear({ domain: [yLo, yHi], range: [innerH, 0] }),
    [yLo, yHi, innerH],
  );

  const yt = useMemo(() => yTicks(yLo, yHi, metric), [yLo, yHi, metric]);
  const xt = useMemo(() => xTicks(yearRange[0], yearRange[1]), [yearRange]);

  const lineData = useMemo(
    () =>
      players.map(p => {
        const pts = p.seasons.filter(
          s => s.season >= yearRange[0] && s.season <= yearRange[1] && s[metric] != null,
        );
        return { player: p, pts };
      }),
    [players, metric, yearRange],
  );

  const { tooltipData, tooltipLeft, tooltipTop, showTooltip, hideTooltip } =
    useTooltip<TooltipData>();

  function handleMouseMove(e: React.MouseEvent<SVGRectElement>) {
    const point = localPoint(e);
    if (!point) return;
    const px = point.x - MARGIN.left;
    if (px < 0 || px > innerW) { hideTooltip(); return; }
    const season = Math.round(xScale.invert(px));
    if (season < yearRange[0] || season > yearRange[1]) { hideTooltip(); return; }

    const rows = lineData
      .map(({ player, pts }) => {
        const pt = pts.find(s => s.season === season);
        return pt ? { player, val: pt[metric] as number } : null;
      })
      .filter((r): r is { player: ChartPlayer; val: number } => r != null);

    if (!rows.length) { hideTooltip(); return; }

    const awardRows = players.flatMap(p =>
      (p.awards ?? [])
        .filter(a => a.year === season && CHART_KINDS.has(a.kind))
        .map(a => ({ player: p, award: a })),
    );

    showTooltip({
      tooltipData: { season, rows, awardRows },
      tooltipLeft: point.x,
      tooltipTop: point.y,
    });
  }

  return (
    <div style={{ position: 'relative' }}>
      <svg className="chart" viewBox={`0 0 ${width} ${height}`}>
        {/* Transparent overlay to capture mouse events across the full chart area */}
        <rect
          x={MARGIN.left}
          y={MARGIN.top}
          width={innerW}
          height={innerH}
          fill="transparent"
          onMouseMove={handleMouseMove}
          onMouseLeave={hideTooltip}
        />

        <Group top={MARGIN.top} left={MARGIN.left}>
          <GridRows
            scale={yScale}
            width={innerW}
            tickValues={yt}
            stroke="var(--line-soft)"
            strokeDasharray="2,4"
          />

          {metric === 'war' && yLo < 0 && (
            <line
              className="chart-zero"
              x1={0} x2={innerW}
              y1={yScale(0)} y2={yScale(0)}
            />
          )}

          <AxisLeft
            scale={yScale}
            tickValues={yt}
            tickFormat={v => fmtMetric(metric, v as number)}
            tickLabelProps={{ fill: 'var(--text-3)', fontSize: 10.5, fontFamily: 'var(--font-mono)', textAnchor: 'end', dx: -4, dy: '0.32em' }}
            hideAxisLine
            hideTicks
          />

          <AxisBottom
            scale={xScale}
            top={innerH}
            tickValues={xt}
            tickFormat={v => String(v)}
            tickLabelProps={{ fill: 'var(--text-3)', fontSize: 10.5, fontFamily: 'var(--font-mono)', textAnchor: 'middle', dy: '1em' }}
            stroke="var(--line)"
            tickStroke="transparent"
          />

          {tooltipData && (
            <line
              className="crosshair"
              x1={xScale(tooltipData.season)} x2={xScale(tooltipData.season)}
              y1={0} y2={innerH}
            />
          )}

          {lineData.map(({ player, pts }) => {
            const dim = hoverPlayerId !== null && hoverPlayerId !== player.id;
            const hov = hoverPlayerId === player.id;
            return (
              <LinePath
                key={player.id}
                data={pts}
                x={s => xScale(s.season)}
                y={s => yScale(s[metric] as number)}
                curve={curveCatmullRom}
                className={`line ${dim ? 'is-dim' : ''} ${hov ? 'is-hover' : ''}`}
                stroke={player.color}
                onMouseEnter={() => setHoverPlayerId(player.id)}
                onMouseLeave={() => setHoverPlayerId(null)}
              />
            );
          })}

          {lineData.map(({ player, pts }) =>
            pts.map(s => {
              const isHoverSeason = tooltipData?.season === s.season;
              const dim = hoverPlayerId !== null && hoverPlayerId !== player.id;
              return (
                <circle
                  key={`${player.id}-${s.season}`}
                  className="dot"
                  cx={xScale(s.season)}
                  cy={yScale(s[metric] as number)}
                  r={isHoverSeason ? 4.5 : 2.2}
                  fill={player.color}
                  stroke="#0f1117"
                  strokeWidth={1.5}
                  opacity={dim ? 0.2 : 1}
                />
              );
            }),
          )}

          {lineData.map(({ player, pts }) =>
            pts.map(s => {
              const ann = topAnnotation(player.awards, s.season);
              if (!ann || s[metric] == null) return null;
              const dim = hoverPlayerId !== null && hoverPlayerId !== player.id;
              return (
                <g key={`ann-${player.id}-${s.season}`} opacity={dim ? 0.2 : 1}>
                  <ChartGlyph
                    kind={ann.kind}
                    color={player.color}
                    cx={xScale(s.season)}
                    cy={yScale(s[metric] as number)}
                  />
                </g>
              );
            }),
          )}
        </Group>
      </svg>

      {tooltipData && tooltipLeft != null && tooltipTop != null && (
        <TooltipWithBounds
          left={tooltipLeft}
          top={tooltipTop}
          style={{
            position: 'absolute',
            pointerEvents: 'none',
            background: 'rgba(20,23,33,0.96)',
            border: '1px solid var(--line)',
            borderRadius: 10,
            padding: '10px 12px',
            minWidth: 180,
            fontSize: 12,
            backdropFilter: 'blur(6px)',
          }}
        >
          <div className="tooltip-season">{tooltipData.season}</div>
          {tooltipData.rows
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
          {tooltipData.awardRows.length > 0 && (
            <div style={{ borderTop: '1px solid var(--line)', marginTop: 6, paddingTop: 6, display: 'flex', flexDirection: 'column', gap: 3 }}>
              {tooltipData.awardRows.map(({ player, award }) => (
                <div key={award.id} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <AnnotationGlyph kind={award.kind} color={player.color} size={11} />
                  <span style={{ color: player.color, fontSize: 11 }}>{player.name}</span>
                  <span style={{ color: 'var(--text-2)', fontSize: 11 }}>{AWARD_LABELS[award.kind]}</span>
                </div>
              ))}
            </div>
          )}
        </TooltipWithBounds>
      )}
    </div>
  );
}
