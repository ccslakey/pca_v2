import { PlayerCard } from 'pca-design-system';
import { trout, judge, kershaw, ohtani, noop } from './_players';

export const Batter = () => (
  <div className="cards-row" style={{ width: 260 }}>
    <PlayerCard player={trout} metric="war" isHovered={false}
      onHoverEnter={noop} onHoverLeave={noop} onRemove={noop} />
  </div>
);

export const PitcherByERA = () => (
  <div className="cards-row" style={{ width: 260 }}>
    <PlayerCard player={kershaw} metric="era" isHovered={false}
      onHoverEnter={noop} onHoverLeave={noop} onRemove={noop} />
  </div>
);

export const Hovered = () => (
  <div className="cards-row" style={{ width: 260 }}>
    <PlayerCard player={ohtani} metric="hr" isHovered
      onHoverEnter={noop} onHoverLeave={noop} onRemove={noop} />
  </div>
);

export const ComparisonRow = () => (
  <div className="cards-row" style={{ width: 720 }}>
    {[trout, judge, ohtani].map((p) => (
      <PlayerCard key={p.id} player={p} metric="hr" isHovered={false}
        onHoverEnter={noop} onHoverLeave={noop} onRemove={noop} />
    ))}
  </div>
);
