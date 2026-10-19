import { Sparkline, playerColor } from 'pca-design-system';
import { trout, kershaw } from './_players';

// Sparkline fills its parent's width (visx ParentSize) - give it a sized container.
const war = trout.seasons.map((s) => s.war).filter((v): v is number => v != null);
const era = kershaw.seasons.map((s) => s.era).filter((v): v is number => v != null);

export const WARSeries = () => (
  <div style={{ width: 260 }}>
    <Sparkline data={war} color={playerColor(trout.id)} />
  </div>
);

// invert flips the y-axis for lower-is-better stats.
export const InvertedERA = () => (
  <div style={{ width: 260 }}>
    <Sparkline data={era} color={playerColor(kershaw.id)} invert height={48} />
  </div>
);
