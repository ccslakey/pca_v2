import { PlayerCard, PlayerCardSkeleton } from 'pca-design-system';
import { trout, noop } from './_players';

export const Loading = () => (
  <div className="cards-row" style={{ width: 260 }}>
    <PlayerCardSkeleton />
  </div>
);

export const RowWhileLoading = () => (
  <div className="cards-row" style={{ width: 720 }}>
    <PlayerCard player={trout} metric="war" isHovered={false}
      onHoverEnter={noop} onHoverLeave={noop} onRemove={noop} />
    <PlayerCardSkeleton />
    <PlayerCardSkeleton />
  </div>
);
