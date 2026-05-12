import { useMemo } from 'react';
import { ParentSize } from '@visx/responsive';
import { LinePath, AreaClosed } from '@visx/shape';
import { scaleLinear } from '@visx/scale';
import { curveLinear } from 'd3-shape';

interface Props {
  data: number[];
  color: string;
  height?: number;
  invert?: boolean;
}

function SparkInner({ data, color, width, height, invert }: Props & { width: number }) {
  const lo = Math.min(...data);
  const hi = Math.max(...data);

  const xScale = useMemo(
    () => scaleLinear({ domain: [0, data.length - 1], range: [0, width] }),
    [data.length, width],
  );
  const yScale = useMemo(() => {
    const yLo = lo === hi ? lo - 1 : lo;
    const yHi = lo === hi ? hi + 1 : hi;
    return scaleLinear({
      domain: invert ? [yHi, yLo] : [yLo, yHi],
      range: [height! - 2, 4],
    });
  }, [lo, hi, height, invert]);

  const points = data.map((v, i) => ({ v, i }));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ display: 'block', width: '100%', height }}>
      <defs>
        <linearGradient id={`spark-${color.replace(/[^a-z0-9]/gi, '')}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.18} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <AreaClosed
        data={points}
        x={d => xScale(d.i)}
        y={d => yScale(d.v)}
        yScale={yScale}
        curve={curveLinear}
        fill={`url(#spark-${color.replace(/[^a-z0-9]/gi, '')})`}
      />
      <LinePath
        data={points}
        x={d => xScale(d.i)}
        y={d => yScale(d.v)}
        curve={curveLinear}
        stroke={color}
        strokeWidth={1.6}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {points.length > 0 && (() => {
        const last = points[points.length - 1];
        return <circle cx={xScale(last.i)} cy={yScale(last.v)} r={2.5} fill={color} />;
      })()}
    </svg>
  );
}

export function Sparkline({ data, color, height = 36, invert = false }: Props) {
  if (!data.length) return null;
  return (
    <ParentSize>
      {({ width }) =>
        width > 0 ? (
          <SparkInner data={data} color={color} width={width} height={height} invert={invert} />
        ) : null
      }
    </ParentSize>
  );
}
