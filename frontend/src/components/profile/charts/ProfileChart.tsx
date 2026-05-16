import { useMemo } from "react";
import { scaleLinear } from "@visx/scale";
import { LinePath, AreaClosed } from "@visx/shape";
import { Group } from "@visx/group";
import { GridRows } from "@visx/grid";
import { AxisLeft, AxisBottom } from "@visx/axis";
import { useTooltip, TooltipWithBounds } from "@visx/tooltip";
import { localPoint } from "@visx/event";
import { curveCatmullRom } from "d3-shape";
import type { ChartPlayer, MetricId } from "../../../types";
import { fmtMetric, yTicks, yDomain, xTicks } from "../../../utils/chart";

interface Props {
  player: ChartPlayer;
  metric: MetricId;
  width: number;
  height?: number;
}

interface TooltipData {
  season: number;
  val: number;
}

const MARGIN = { top: 18, right: 24, bottom: 30, left: 44 };

export function ProfileChart({ player, metric, width, height = 320 }: Props) {
  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

  const data = useMemo(
    () => player.seasons.filter((s) => s[metric] != null),
    [player, metric],
  );

  const xDomain = useMemo<[number, number]>(() => {
    if (!data.length) return [2000, 2024];
    return [data[0].season, data[data.length - 1].season];
  }, [data]);

  const allVals = useMemo(
    () => data.map((s) => s[metric] as number),
    [data, metric],
  );
  const [yLo, yHi] = useMemo(() => yDomain(allVals, metric), [allVals, metric]);

  const xScale = useMemo(
    () => scaleLinear({ domain: xDomain, range: [0, innerW] }),
    [xDomain, innerW],
  );
  const yScale = useMemo(
    () => scaleLinear({ domain: [yLo, yHi], range: [innerH, 0] }),
    [yLo, yHi, innerH],
  );

  const yt = useMemo(() => yTicks(yLo, yHi, metric), [yLo, yHi, metric]);
  const xt = useMemo(() => xTicks(xDomain[0], xDomain[1]), [xDomain]);

  const gradId = `profile-grad-${player.id}`;

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
    const season = Math.round(xScale.invert(px));
    const pt = data.find((s) => s.season === season);
    if (!pt) {
      hideTooltip();
      return;
    }
    showTooltip({
      tooltipData: { season, val: pt[metric] as number },
      tooltipLeft: point.x,
      tooltipTop: point.y,
    });
  }

  if (!data.length) {
    return (
      <div
        style={{
          height,
          display: "grid",
          placeItems: "center",
          color: "var(--text-3)",
          fontSize: 13,
        }}
      >
        No {metric.toUpperCase()} data
      </div>
    );
  }

  return (
    <div style={{ position: "relative" }}>
      <svg className="chart" viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={player.color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={player.color} stopOpacity={0} />
          </linearGradient>
        </defs>

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

          <AreaClosed
            data={data}
            x={(s) => xScale(s.season)}
            y={(s) => yScale(s[metric] as number)}
            yScale={yScale}
            curve={curveCatmullRom}
            fill={`url(#${gradId})`}
          />

          <LinePath
            data={data}
            x={(s) => xScale(s.season)}
            y={(s) => yScale(s[metric] as number)}
            curve={curveCatmullRom}
            stroke={player.color}
            strokeWidth={2.2}
            strokeLinecap="round"
          />

          {data.map((s) => (
            <circle
              key={s.season}
              cx={xScale(s.season)}
              cy={yScale(s[metric] as number)}
              r={tooltipData?.season === s.season ? 5 : 2.6}
              fill={player.color}
              stroke="#0f1117"
              strokeWidth={1.5}
            />
          ))}

          {tooltipData && (
            <line
              className="crosshair"
              x1={xScale(tooltipData.season)}
              x2={xScale(tooltipData.season)}
              y1={0}
              y2={innerH}
            />
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
            border: "1px solid var(--line)",
            borderRadius: 10,
            padding: "10px 12px",
            minWidth: 140,
            fontSize: 12,
            backdropFilter: "blur(6px)",
          }}
        >
          <div className="tooltip-season">{tooltipData.season}</div>
          <div className="tooltip-row">
            <span className="l">
              <span className="swatch" style={{ background: player.color }} />
              {metric.toUpperCase()}
            </span>
            <span className="v">{fmtMetric(metric, tooltipData.val)}</span>
          </div>
        </TooltipWithBounds>
      )}
    </div>
  );
}
