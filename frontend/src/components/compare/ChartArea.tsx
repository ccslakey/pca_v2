import { ParentSize } from '@visx/responsive';
import { CareerChart } from './CareerChart';
import { BrushChart } from './BrushChart';
import { useAgingCurve } from '../../hooks';
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
  const allBatters = players.length > 0 && players.every((p) => p.isBatter && !p.isPitcher);
  const allPitchers = players.length > 0 && players.every((p) => p.isPitcher);
  const curveRole = allBatters ? 'B' : allPitchers ? 'P' : null;
  const { data: agingCurve } = useAgingCurve(curveRole);

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
            agingCurve={agingCurve}
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
