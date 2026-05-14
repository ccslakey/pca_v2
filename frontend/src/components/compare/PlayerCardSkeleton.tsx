import './PlayerCard.scss';
import { Skeleton } from '../Skeleton';

export function PlayerCardSkeleton() {
  return (
    <div className="player-card">
      <div className="accent-bar" style={{ background: 'var(--line)' }} />
      <div className="player-card-head">
        <Skeleton variant="circle" width={32} height={32} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Skeleton width="70%" height={13} />
          <Skeleton width="50%" height={11} style={{ marginTop: 5 }} />
        </div>
      </div>
      <div className="player-card-stats">
        <div className="stat">
          <Skeleton width={60} height={9} />
          <Skeleton width={36} height={17} style={{ marginTop: 4 }} />
        </div>
        <div className="stat">
          <Skeleton width={70} height={9} />
          <Skeleton width={40} height={17} style={{ marginTop: 4 }} />
        </div>
      </div>
    </div>
  );
}
