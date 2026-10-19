import { ProfileChart, playerColor } from 'pca-design-system';
import { griffey, kershaw } from './_players';

export const BatterWAR = () => (
  <div className="panel" style={{ width: 760 }}>
    <ProfileChart player={{ ...griffey, color: playerColor(griffey.id) }} metric="war" width={720} height={280} />
  </div>
);

export const PitcherERA = () => (
  <div className="panel" style={{ width: 760 }}>
    <ProfileChart player={{ ...kershaw, color: playerColor(kershaw.id) }} metric="era" width={720} height={280} />
  </div>
);
