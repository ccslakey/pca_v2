import { useState } from 'react';
import { MetricToggle } from 'pca-design-system';
import type { MetricId, XMode } from 'pca-design-system';

export const Interactive = () => {
  const [metric, setMetric] = useState<MetricId>('war');
  const [xMode, setXMode] = useState<XMode>('year');
  const [showGlyphs, setShowGlyphs] = useState(true);
  return (
    <div style={{ width: '100%' }}>
      <MetricToggle metric={metric} onChange={setMetric} xMode={xMode} onXModeChange={setXMode}
        showGlyphs={showGlyphs} onToggleGlyphs={() => setShowGlyphs((g) => !g)} />
    </div>
  );
};

export const ERAByAgeGlyphsHidden = () => (
  <div style={{ width: '100%' }}>
    <MetricToggle metric="era" onChange={() => {}} xMode="age" onXModeChange={() => {}}
      showGlyphs={false} onToggleGlyphs={() => {}} />
  </div>
);
