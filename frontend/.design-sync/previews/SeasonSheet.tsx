import { SeasonSheet, playerColor, peakSeason } from 'pca-design-system';
import { ohtani, noop } from './_players';

// Bottom sheet shown when a season row is tapped on mobile. It is absolutely
// positioned, so it needs a positioned phone-height screen behind it - in the
// app that's .m-app/.m-screen.
const peak = peakSeason(ohtani.seasons, 'war');
const season = ohtani.seasons.find((s) => s.season === peak?.season) ?? ohtani.seasons[0];

export const PeakSeason = () => (
  <div className="m-app" style={{ width: 390, height: 680 }}>
    <SeasonSheet player={ohtani} season={season}
      awards={ohtani.awards.filter((a) => a.year === season.season)}
      team="LAA" color={playerColor(ohtani.id)} onClose={noop} />
  </div>
);
