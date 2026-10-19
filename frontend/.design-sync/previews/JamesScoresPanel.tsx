import { JamesScoresPanel } from 'pca-design-system';
import { griffey, kershaw, ohtani, james } from './_players';

export const Batter = () => (
  <div style={{ width: 360 }}>
    <JamesScoresPanel james={james[griffey.id]} isBatter={griffey.isBatter} isPitcher={griffey.isPitcher} />
  </div>
);

export const Pitcher = () => (
  <div style={{ width: 360 }}>
    <JamesScoresPanel james={james[kershaw.id]} isBatter={kershaw.isBatter} isPitcher={kershaw.isPitcher} />
  </div>
);

export const TwoWay = () => (
  <div style={{ width: 360 }}>
    <JamesScoresPanel james={james[ohtani.id]} isBatter={ohtani.isBatter} isPitcher={ohtani.isPitcher} />
  </div>
);
