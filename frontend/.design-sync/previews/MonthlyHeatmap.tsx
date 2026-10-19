import { MonthlyHeatmap, playerColor } from 'pca-design-system';
import { trout, judge } from './_players';

export const LastSixSeasons = () => (
  <div className="panel" style={{ width: 660 }}>
    <MonthlyHeatmap seasons={trout.seasons} color={playerColor(trout.id)} />
  </div>
);

export const AnotherPlayerColor = () => (
  <div className="panel" style={{ width: 660 }}>
    <MonthlyHeatmap seasons={judge.seasons} color={playerColor(judge.id)} />
  </div>
);
