import { ParentSize } from '@visx/responsive';
import { CareerChart } from './CareerChart';
import { BrushChart } from './BrushChart';
import type { ChartPlayer, MetricId, XMode } from '../../types';

interface Props {
  players: ChartPlayer[];
  metric: MetricId;
  xMode: XMode;
  xRange: [number, number];
  fullRange: [number, number];
  showGlyphs: boolean;
  hoverPlayerId: string | null;
  setHoverPlayerId: (id: string | null) => void;
  setXRange: (r: [number, number]) => void;
}

export function ChartArea({
  players,
  metric,
  xMode,
  xRange,
  fullRange,
  showGlyphs,
  hoverPlayerId,
  setHoverPlayerId,
  setXRange,
}: Props) {
  return (
    <ParentSize>
      {({ width }) => (
        <>
          <CareerChart
            players={players}
            metric={metric}
            xMode={xMode}
            xRange={xRange}
            showGlyphs={showGlyphs}
            hoverPlayerId={hoverPlayerId}
            setHoverPlayerId={setHoverPlayerId}
            width={width}
          />
          <BrushChart
            players={players}
            metric={metric}
            xMode={xMode}
            xRange={xRange}
            fullRange={fullRange}
            setXRange={setXRange}
            width={width}
          />
        </>
      )}
    </ParentSize>
  );
}
