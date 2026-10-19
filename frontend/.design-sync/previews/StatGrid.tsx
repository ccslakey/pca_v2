import { StatGrid, careerWar, peakSeason, sumMetric } from 'pca-design-system';
import type { ChartPlayer } from 'pca-design-system';
import { griffey, kershaw, ohtani } from './_players';

// Same derivations ProfilePage uses.
const statsFor = (p: ChartPlayer) => ({
  player: p,
  war: careerWar(p.seasons),
  peak: peakSeason(p.seasons, 'war'),
  careerHR: sumMetric(p.seasons, 'hr') ?? 0,
  careerSO: sumMetric(p.seasons, 'so') ?? 0,
  careerAVG: sumMetric(p.seasons, 'avg'),
  careerOPS: sumMetric(p.seasons, 'ops'),
  careerERA: sumMetric(p.seasons, 'era'),
});

export const Batter = () => (
  <div style={{ width: '100%' }}><StatGrid {...statsFor(griffey)} /></div>
);

export const Pitcher = () => (
  <div style={{ width: '100%' }}><StatGrid {...statsFor(kershaw)} /></div>
);

export const TwoWay = () => (
  <div style={{ width: '100%' }}><StatGrid {...statsFor(ohtani)} /></div>
);
