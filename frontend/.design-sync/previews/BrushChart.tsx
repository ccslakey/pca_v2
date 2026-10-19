import { useState } from 'react';
import { BrushChart, CareerChart } from 'pca-design-system';
import { trout, judge, griffey, fullRange } from './_players';

const batters = [trout, judge, griffey];

// The range scrubber under CareerChart, composed the way the app's ChartArea
// does: both share xRange; dragging the brush handles narrows the chart above.
// The brush starts at fullRange (its initial position is not driven by xRange).
export const UnderCareerChart = () => {
  const full = fullRange(batters, 'year');
  const [range, setRange] = useState<[number, number]>(full);
  const [hover, setHover] = useState<string | null>(null);
  return (
    <div className="chart-card">
      <CareerChart players={batters} metric="war" xMode="year" xRange={range} showGlyphs={false}
        hoverPlayerId={hover} setHoverPlayerId={setHover} width={800} height={300} />
      <BrushChart players={batters} metric="war" xMode="year" xRange={range} fullRange={full}
        setXRange={setRange} width={800} />
    </div>
  );
};
