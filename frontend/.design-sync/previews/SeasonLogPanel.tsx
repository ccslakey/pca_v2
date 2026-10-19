import { SeasonLogPanel, peakSeason, playerColor } from 'pca-design-system';
import { judge, ohtani, noop } from './_players';

export const Batter = () => (
  <div style={{ width: 560 }}>
    <SeasonLogPanel player={judge} color={playerColor(judge.id)}
      peak={peakSeason(judge.seasons, 'war')} tab="standard" setTab={noop} />
  </div>
);

export const TwoWayPlayer = () => (
  <div style={{ width: 560 }}>
    <SeasonLogPanel player={ohtani} color={playerColor(ohtani.id)}
      peak={peakSeason(ohtani.seasons, 'war')} tab="standard" setTab={noop} />
  </div>
);
