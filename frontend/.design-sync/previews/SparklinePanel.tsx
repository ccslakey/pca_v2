import { SparklinePanel, METRICS, playerColor } from 'pca-design-system';
import type { ChartPlayer } from 'pca-design-system';
import { judge, kershaw } from './_players';

// ProfilePage's availableMetrics rule.
const metricsFor = (p: ChartPlayer) => METRICS.filter((m) => {
  if (m.id === 'era') return p.isPitcher;
  if (['hr', 'avg', 'ops'].includes(m.id)) return p.isBatter;
  return true;
});

export const Batter = () => (
  <div style={{ width: 760 }}>
    <SparklinePanel player={judge} color={playerColor(judge.id)} availableMetrics={metricsFor(judge)} />
  </div>
);

export const Pitcher = () => (
  <div style={{ width: 760 }}>
    <SparklinePanel player={kershaw} color={playerColor(kershaw.id)}
      availableMetrics={metricsFor(kershaw).filter((m) => !['hr', 'avg', 'ops'].includes(m.id))} />
  </div>
);
