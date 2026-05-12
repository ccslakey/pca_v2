import './BrushChart.scss';
import { useMemo, useRef } from 'react';
import { scaleLinear } from '@visx/scale';
import { AreaClosed } from '@visx/shape';
import { Group } from '@visx/group';
import Brush from '@visx/brush/lib/Brush';
import type { Bounds } from '@visx/brush/lib/types';
import type BaseBrush from '@visx/brush/lib/BaseBrush';
import type { BrushHandleRenderProps } from '@visx/brush/lib/BrushHandle';
import { curveCatmullRom } from 'd3-shape';
import type { ChartPlayer, MetricId, XMode } from '../../types';

interface Props {
  players: ChartPlayer[];
  metric: MetricId;
  xMode: XMode;
  xRange: [number, number];
  fullRange: [number, number];
  setXRange: (r: [number, number]) => void;
  width: number;
}

const HEIGHT = 60;
const MARGIN = { top: 6, right: 28, bottom: 18, left: 44 };

const SELECTED_BOX_STYLE: React.SVGProps<SVGRectElement> = {
  fill: 'oklch(0.72 0.14 240 / 0.10)',
  stroke: 'oklch(0.72 0.14 240 / 0.55)',
  strokeWidth: 1,
};

function BrushHandle({ x, y, height, isBrushActive }: BrushHandleRenderProps) {
  if (!isBrushActive) return null;
  const cy = y + height / 2;
  return (
    <rect
      x={x - 3}
      y={cy - 8}
      width={6}
      height={16}
      rx={2}
      className="brush-handle"
      style={{ cursor: 'ew-resize' }}
    />
  );
}

export function BrushChart({ players, metric, xMode, xRange, fullRange, setXRange, width }: Props) {
  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, HEIGHT - MARGIN.top - MARGIN.bottom);

  const brushRef = useRef<BaseBrush | null>(null);

  const xScale = useMemo(
    () => scaleLinear({ domain: fullRange, range: [0, innerW] }),
    [fullRange, innerW],
  );

  const maxVals = useMemo(() => {
    const map = new Map<number, number>();
    players.forEach(p =>
      p.seasons.forEach(s => {
        const key = xMode === 'age' ? s.age : s.season;
        if (key == null) return;
        const v = s[metric];
        if (v == null) return;
        const cur = map.get(key);
        const cmp = metric === 'era' ? Math.min : Math.max;
        map.set(key, cur == null ? v : cmp(cur, v));
      }),
    );
    return map;
  }, [players, metric, xMode]);

  const yDomainVals = useMemo(() => {
    const vals = [...maxVals.values()];
    return vals.length
      ? [Math.min(...vals, 0), Math.max(...vals)] as [number, number]
      : [0, 1] as [number, number];
  }, [maxVals]);

  const yScale = useMemo(
    () => scaleLinear({ domain: yDomainVals, range: [innerH, 0] }),
    [yDomainVals, innerH],
  );

  const sparklineData = useMemo(
    () =>
      [...maxVals.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([xKey, val]) => ({ xKey, val })),
    [maxVals],
  );

  const initialBrushPosition = useMemo(() => ({
    start: { x: xScale(xRange[0]) },
    end:   { x: xScale(xRange[1]) },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [fullRange[0], fullRange[1], innerW]);

  function onBrushChange(bounds: Bounds | null) {
    if (!bounds) return;
    const lo = Math.round(bounds.x0);
    const hi = Math.round(bounds.x1);
    setXRange([
      Math.max(fullRange[0], Math.min(lo, fullRange[1])),
      Math.max(fullRange[0], Math.min(hi, fullRange[1])),
    ]);
  }

  const brushKey = `${fullRange[0]}-${fullRange[1]}-${innerW}-${xMode}`;

  const fmt = (v: number) => xMode === 'age' ? `${v}` : `${v}`;

  return (
    <div className="brush-wrap">
      <svg className="brush-svg" viewBox={`0 0 ${width} ${HEIGHT}`}>
        <Group top={MARGIN.top} left={MARGIN.left}>
          <AreaClosed
            data={sparklineData}
            x={d => xScale(d.xKey)}
            y={d => yScale(d.val)}
            yScale={yScale}
            curve={curveCatmullRom}
            fill="rgba(255,255,255,0.06)"
            stroke="rgba(255,255,255,0.12)"
            strokeWidth={1}
          />

          <Brush
            key={brushKey}
            innerRef={brushRef}
            xScale={xScale}
            yScale={yScale}
            width={innerW}
            height={innerH}
            initialBrushPosition={initialBrushPosition}
            onChange={onBrushChange}
            brushDirection="horizontal"
            resizeTriggerAreas={['left', 'right']}
            handleSize={10}
            selectedBoxStyle={SELECTED_BOX_STYLE}
            disableDraggingSelection={false}
            useWindowMoveEvents
            renderBrushHandle={props => <BrushHandle {...props} />}
          />

          <text className="brush-label" x={xScale(xRange[0])} y={innerH + 14} textAnchor="middle">{fmt(xRange[0])}</text>
          <text className="brush-label" x={xScale(xRange[1])} y={innerH + 14} textAnchor="middle">{fmt(xRange[1])}</text>
          <text x={-8}         y={innerH / 2} dy="0.32em" textAnchor="end"   className="brush-label" opacity={0.5}>{fmt(fullRange[0])}</text>
          <text x={innerW + 8} y={innerH / 2} dy="0.32em" textAnchor="start" className="brush-label" opacity={0.5}>{fmt(fullRange[1])}</text>
        </Group>
      </svg>
    </div>
  );
}
