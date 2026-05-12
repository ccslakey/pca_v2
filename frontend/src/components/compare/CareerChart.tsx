import { useMemo } from "react";
import { scaleLinear } from "@visx/scale";
import { LinePath } from "@visx/shape";
import { Group } from "@visx/group";
import { GridRows } from "@visx/grid";
import { AxisLeft, AxisBottom } from "@visx/axis";
import { useTooltip, TooltipWithBounds } from "@visx/tooltip";
import { localPoint } from "@visx/event";
import { curveCatmullRom } from "d3-shape";
import type {
  AwardKind,
  ChartPlayer,
  MetricId,
  PlayerAward,
  XMode,
} from "../../types";
import { fmtMetric, yTicks, yDomain, xTicks } from "../../utils/chart";
import { AnnotationGlyph } from "../AnnotationGlyph";

const CHART_KINDS = new Set<AwardKind>([
  "tc_b",
  "tc_p",
  "mvp",
  "cy",
  "ws",
  "roty",
  "postmvp",
  "ss",
  "gg",
  "bat_title",
  "era_title",
  "all_mlb",
  "asg",
]);

// Lower number = shown when two awards share the same year
const AWARD_PRIORITY: Partial<Record<AwardKind, number>> = {
  tc_b: 0,
  tc_p: 0,
  mvp: 1,
  cy: 2,
  ws: 3,
  roty: 4,
  postmvp: 5,
  ss: 6,
  gg: 7,
  bat_title: 8,
  era_title: 8,
  all_mlb: 9,
  asg: 11,
};

const AWARD_LABELS: Partial<Record<AwardKind, string>> = {
  mvp: "MVP",
  cy: "Cy Young",
  gg: "Gold Glove",
  asg: "All-Star",
  roty: "Rookie of Year",
  ws: "World Series",
  hof: "Hall of Fame",
  ss: "Silver Slugger",
  tc_b: "Triple Crown (batting)",
  tc_p: "Triple Crown (pitching)",
  bat_title: "Batting Title",
  era_title: "ERA Title",
  all_mlb: "All-MLB Team",
  postmvp: "Postseason MVP",
};

/** Top-priority chart annotation for a player in a given year, null if none. */
function topAnnotation(
  awards: PlayerAward[],
  year: number,
): PlayerAward | null {
  let best: PlayerAward | null = null;
  for (const a of awards) {
    if (a.year !== year || !CHART_KINDS.has(a.kind)) continue;
    if (
      best === null ||
      (AWARD_PRIORITY[a.kind] ?? 99) < (AWARD_PRIORITY[best.kind] ?? 99)
    ) {
      best = a;
    }
  }
  return best;
}

function ChartGlyph({
  kind,
  color,
  cx,
  cy,
}: {
  kind: AwardKind;
  color: string;
  cx: number;
  cy: number;
}) {
  const R = 11;
  const S = R * 1.25;
  return (
    <g pointerEvents="none">
      <circle
        cx={cx}
        cy={cy}
        r={R}
        fill="var(--bg-1)"
        stroke={color}
        strokeWidth={1.5}
      />
      <svg
        x={cx - S / 2}
        y={cy - S / 2}
        width={S}
        height={S}
        overflow="visible"
      >
        <AnnotationGlyph kind={kind} color={color} size={S} />
      </svg>
    </g>
  );
}

interface Props {
  players: ChartPlayer[];
  metric: MetricId;
  xMode: XMode;
  xRange: [number, number];
  showGlyphs: boolean;
  hoverPlayerId: string | null;
  setHoverPlayerId: (id: string | null) => void;
  width: number;
  height?: number;
}

interface TooltipData {
  xVal: number;
  rows: { player: ChartPlayer; val: number; actualYear: number }[];
  awardRows: { player: ChartPlayer; award: PlayerAward }[];
}

const MARGIN = { top: 18, right: 28, bottom: 30, left: 44 };

export function CareerChart({
  players,
  metric,
  xMode,
  xRange,
  showGlyphs,
  hoverPlayerId,
  setHoverPlayerId,
  width,
  height = 420,
}: Props) {
  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

  const xVal = (s: { season: number; age: number | null }) =>
    xMode === "age" ? (s.age ?? null) : s.season;

  const allVals = useMemo(() => {
    const vals: number[] = [];
    players.forEach((p) =>
      p.seasons.forEach((s) => {
        const x = xVal(s);
        if (x == null || x < xRange[0] || x > xRange[1]) return;
        const v = s[metric];
        if (v != null) vals.push(v);
      }),
    );
    return vals;
  }, [players, metric, xRange, xMode]); // eslint-disable-line react-hooks/exhaustive-deps

  const [yLo, yHi] = useMemo(() => yDomain(allVals, metric), [allVals, metric]);

  const xScale = useMemo(
    () => scaleLinear({ domain: xRange, range: [0, innerW] }),
    [xRange, innerW],
  );
  const yScale = useMemo(
    () => scaleLinear({ domain: [yLo, yHi], range: [innerH, 0] }),
    [yLo, yHi, innerH],
  );

  const yt = useMemo(() => yTicks(yLo, yHi, metric), [yLo, yHi, metric]);
  const xt = useMemo(() => xTicks(xRange[0], xRange[1]), [xRange]);

  const lineData = useMemo(
    () =>
      players.map((p) => {
        const pts = p.seasons.filter((s) => {
          const x = xVal(s);
          return (
            x != null && x >= xRange[0] && x <= xRange[1] && s[metric] != null
          );
        });
        return { player: p, pts };
      }),
    [players, metric, xRange, xMode], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const { tooltipData, tooltipLeft, tooltipTop, showTooltip, hideTooltip } =
    useTooltip<TooltipData>();

  function handleMouseMove(e: React.MouseEvent<SVGRectElement>) {
    const point = localPoint(e);
    if (!point) return;
    const px = point.x - MARGIN.left;
    if (px < 0 || px > innerW) {
      hideTooltip();
      return;
    }
    const hovered = Math.round(xScale.invert(px));
    if (hovered < xRange[0] || hovered > xRange[1]) {
      hideTooltip();
      return;
    }

    const rows = lineData
      .map(({ player, pts }) => {
        const pt = pts.find(
          (s) => (xMode === "age" ? s.age : s.season) === hovered,
        );
        return pt
          ? { player, val: pt[metric] as number, actualYear: pt.season }
          : null;
      })
      .filter(
        (r): r is { player: ChartPlayer; val: number; actualYear: number } =>
          r != null,
      );

    if (!rows.length) {
      hideTooltip();
      return;
    }

    const awardRows = rows.flatMap((r) =>
      (r.player.awards ?? [])
        .filter((a) => a.year === r.actualYear && CHART_KINDS.has(a.kind))
        .map((a) => ({ player: r.player, award: a })),
    );

    showTooltip({
      tooltipData: { xVal: hovered, rows, awardRows },
      tooltipLeft: point.x,
      tooltipTop: point.y,
    });
  }

  return (
    <div style={{ position: "relative" }}>
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

          {metric === "war" && yLo < 0 && (
            <line
              className="chart-zero"
              x1={0}
              x2={innerW}
              y1={yScale(0)}
              y2={yScale(0)}
            />
          )}

          <AxisLeft
            scale={yScale}
            tickValues={yt}
            tickFormat={(v) => fmtMetric(metric, v as number)}
            tickLabelProps={{
              fill: "var(--text-3)",
              fontSize: 10.5,
              fontFamily: "var(--font-mono)",
              textAnchor: "end",
              dx: -4,
              dy: "0.32em",
            }}
            hideAxisLine
            hideTicks
          />

          <AxisBottom
            scale={xScale}
            top={innerH}
            tickValues={xt}
            tickFormat={(v) => String(v)}
            tickLabelProps={{
              fill: "var(--text-3)",
              fontSize: 10.5,
              fontFamily: "var(--font-mono)",
              textAnchor: "middle",
              dy: "1em",
            }}
            stroke="var(--line)"
            tickStroke="transparent"
          />

          {tooltipData && (
            <line
              className="crosshair"
              x1={xScale(tooltipData.xVal)}
              x2={xScale(tooltipData.xVal)}
              y1={0}
              y2={innerH}
            />
          )}

          {lineData.map(({ player, pts }) => {
            const dim = hoverPlayerId !== null && hoverPlayerId !== player.id;
            const hov = hoverPlayerId === player.id;
            return (
              <LinePath
                key={player.id}
                data={pts}
                x={(s) => xScale(xVal(s) ?? 0)}
                y={(s) => yScale(s[metric] as number)}
                curve={curveCatmullRom}
                className={`line ${dim ? "is-dim" : ""} ${hov ? "is-hover" : ""}`}
                stroke={player.color}
                onMouseEnter={() => setHoverPlayerId(player.id)}
                onMouseLeave={() => setHoverPlayerId(null)}
              />
            );
          })}

          {lineData.map(({ player, pts }) =>
            pts.map((s) => {
              const sx = xVal(s);
              if (sx == null) return null;
              const isHovered = tooltipData?.xVal === sx;
              const dim = hoverPlayerId !== null && hoverPlayerId !== player.id;
              return (
                <circle
                  key={`${player.id}-${s.season}`}
                  className="dot"
                  cx={xScale(sx)}
                  cy={yScale(s[metric] as number)}
                  r={isHovered ? 4.5 : 2.2}
                  fill={player.color}
                  stroke="#0f1117"
                  strokeWidth={1.5}
                  opacity={dim ? 0.2 : 1}
                />
              );
            }),
          )}

          {showGlyphs && lineData.map(({ player, pts }) =>
            pts.map((s) => {
              const sx = xVal(s);
              if (sx == null) return null;
              const ann = topAnnotation(player.awards, s.season);
              if (!ann || s[metric] == null) return null;
              const dim = hoverPlayerId !== null && hoverPlayerId !== player.id;
              return (
                <g key={`ann-${player.id}-${s.season}`} opacity={dim ? 0.2 : 1}>
                  <ChartGlyph
                    kind={ann.kind}
                    color={player.color}
                    cx={xScale(sx)}
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
            position: "absolute",
            pointerEvents: "none",
            background: "rgba(20,23,33,0.96)",
            border: "1px solid var(--line)",
            borderRadius: 10,
            padding: "10px 12px",
            minWidth: 180,
            fontSize: 12,
            backdropFilter: "blur(6px)",
          }}
        >
          <div className="tooltip-season">
            {xMode === "age" ? `Age ${tooltipData.xVal}` : tooltipData.xVal}
          </div>
          {tooltipData.rows
            .sort((a, b) => (metric === "era" ? a.val - b.val : b.val - a.val))
            .map((r) => (
              <div key={r.player.id} className="tooltip-row">
                <span className="l">
                  <span
                    className="swatch"
                    style={{ background: r.player.color }}
                  />
                  {r.player.name}
                </span>
                <span className="v">{fmtMetric(metric, r.val)}</span>
              </div>
            ))}
          {tooltipData.awardRows.length > 0 && (
            <div
              style={{
                borderTop: "1px solid var(--line)",
                marginTop: 6,
                paddingTop: 6,
                display: "flex",
                flexDirection: "column",
                gap: 3,
              }}
            >
              {tooltipData.awardRows.map(({ player, award }) => (
                <div
                  key={award.id}
                  style={{ display: "flex", alignItems: "center", gap: 5 }}
                >
                  <AnnotationGlyph
                    kind={award.kind}
                    color={player.color}
                    size={11}
                  />
                  <span style={{ color: player.color, fontSize: 11 }}>
                    {player.name}
                  </span>
                  <span style={{ color: "var(--text-2)", fontSize: 11 }}>
                    {AWARD_LABELS[award.kind]}
                  </span>
                </div>
              ))}
            </div>
          )}
        </TooltipWithBounds>
      )}
    </div>
  );
}
