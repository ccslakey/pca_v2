import { HeroSection, peakSeason, playerColor } from 'pca-design-system';
import { griffey, ohtani } from './_players';

// jerseyNum mirrors ProfilePage: (id.charCodeAt(0) % 60) + 1
export const RetiredPlayer = () => (
  <div style={{ width: '100%' }}>
    <HeroSection player={griffey} color={playerColor(griffey.id)}
      jerseyNum={(griffey.id.charCodeAt(0) % 60) + 1} peak={peakSeason(griffey.seasons, 'war')} />
  </div>
);

export const ActivePlayer = () => (
  <div style={{ width: '100%' }}>
    <HeroSection player={ohtani} color={playerColor(ohtani.id)}
      jerseyNum={(ohtani.id.charCodeAt(0) % 60) + 1} peak={peakSeason(ohtani.seasons, 'war')} />
  </div>
);
