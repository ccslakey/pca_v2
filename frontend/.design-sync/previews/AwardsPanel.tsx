import { AwardsPanel, playerColor } from 'pca-design-system';
import { kershaw, ohtani } from './_players';

// Pitching honors only - the full list (26 rows incl. All-Star nods) is long for a card.
export const MajorAwards = () => (
  <div style={{ width: 360 }}>
    <AwardsPanel awards={kershaw.awards.filter((a) => ['cy', 'mvp', 'tc_p', 'ws'].includes(a.kind))}
      color={playerColor(kershaw.id)} />
  </div>
);

export const TwoWayHonors = () => (
  <div style={{ width: 360 }}>
    <AwardsPanel awards={ohtani.awards.filter((a) => a.kind !== 'asg' && a.kind !== 'all_mlb')}
      color={playerColor(ohtani.id)} />
  </div>
);

export const Empty = () => (
  <div style={{ width: 360 }}>
    <AwardsPanel awards={[]} color="var(--accent)" />
  </div>
);
