import { useState } from 'react';
import { CareerArcPanel, METRICS, playerColor } from 'pca-design-system';
import type { MetricId } from 'pca-design-system';
import { griffey, ohtani } from './_players';

export const Batter = () => {
  const [metric, setMetric] = useState<MetricId>('war');
  return (
    <div style={{ width: 760 }}>
      <CareerArcPanel player={griffey} color={playerColor(griffey.id)} metric={metric} setMetric={setMetric}
        availableMetrics={METRICS.filter((m) => m.id !== 'era')} />
    </div>
  );
};

export const TwoWayOPSPlus = () => {
  const [metric, setMetric] = useState<MetricId>('ops_plus');
  return (
    <div style={{ width: 760 }}>
      <CareerArcPanel player={ohtani} color={playerColor(ohtani.id)} metric={metric} setMetric={setMetric}
        availableMetrics={METRICS} />
    </div>
  );
};
