import { useState } from 'react';
import { CareerChart } from 'pca-design-system';
import { trout, judge, griffey, kershaw, maddux, agingBatters, fullRange } from './_players';

const batters = [trout, judge, griffey];

export const WARByYearWithAwards = () => {
  const [hover, setHover] = useState<string | null>(null);
  return (
    <div className="chart-card">
      <CareerChart players={batters} metric="war" xMode="year" xRange={fullRange(batters, 'year')}
        showGlyphs hoverPlayerId={hover} setHoverPlayerId={setHover} width={800} height={380} />
    </div>
  );
};

// Age mode draws the league aging curve behind the players (all-batter or all-pitcher sets).
export const HRByAgeWithAgingCurve = () => {
  const [hover, setHover] = useState<string | null>(null);
  return (
    <div className="chart-card">
      <CareerChart players={batters} metric="hr" xMode="age" xRange={fullRange(batters, 'age')}
        showGlyphs={false} hoverPlayerId={hover} setHoverPlayerId={setHover} width={800} height={380}
        agingCurve={agingBatters} />
    </div>
  );
};

export const PitchersERAOneHovered = () => (
  <div className="chart-card">
    <CareerChart players={[kershaw, maddux]} metric="era" xMode="year"
      xRange={fullRange([kershaw, maddux], 'year')} showGlyphs={false}
      hoverPlayerId={kershaw.id} setHoverPlayerId={() => {}} width={800} height={380} />
  </div>
);
