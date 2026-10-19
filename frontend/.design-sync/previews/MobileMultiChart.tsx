import { MobileMultiChart } from 'pca-design-system';
import { trout, judge, griffey } from './_players';

const batters = [trout, judge, griffey];

export const Overlaid = () => (
  <div className="m-card" style={{ width: 340, margin: 0 }}>
    <MobileMultiChart players={batters} metric="war" />
  </div>
);

export const OnePlayerFocused = () => (
  <div className="m-card" style={{ width: 340, margin: 0 }}>
    <MobileMultiChart players={batters} metric="hr" focusId={judge.id} />
  </div>
);
