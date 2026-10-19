import { MobileChart, playerColor } from 'pca-design-system';
import { trout, kershaw } from './_players';

// MobileProfile renders it in an .m-card with --team-color set to the player color.
export const BatterWAR = () => {
  const color = playerColor(trout.id);
  return (
    <div className="m-card" style={{ width: 340, margin: 0, ['--team-color' as string]: color }}>
      <MobileChart player={trout} metric="war" color={color} width={340} height={180} />
    </div>
  );
};

export const PitcherSO = () => {
  const color = playerColor(kershaw.id);
  return (
    <div className="m-card" style={{ width: 340, margin: 0, ['--team-color' as string]: color }}>
      <MobileChart player={kershaw} metric="so" color={color} width={340} height={180} />
    </div>
  );
};
