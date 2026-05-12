import { ParentSize } from '@visx/responsive';
import '../panel.scss';
import '../../compare/MetricToggle.scss';
import { ProfileChart } from '../charts/ProfileChart';
import { METRICS } from '../../../constants';
import type { ChartPlayer, Metric, MetricId } from '../../../types';

interface Props {
  player:           ChartPlayer;
  color:            string;
  metric:           MetricId;
  setMetric:        (m: MetricId) => void;
  availableMetrics: Metric[];
}

export function CareerArcPanel({ player, color, metric, setMetric, availableMetrics }: Props) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          Career arc
          <span className="muted">{METRICS.find(m => m.id === metric)?.full}</span>
        </div>
        <div className="metric-toggle" style={{ padding: 2 }}>
          {availableMetrics.map(m => (
            <button
              key={m.id}
              className={`metric-pill ${metric === m.id ? 'is-active' : ''}`}
              style={{ padding: '4px 10px', fontSize: 11.5 }}
              onClick={() => setMetric(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>
      <ParentSize>
        {({ width }) => width > 0 && (
          <ProfileChart player={{ ...player, color }} metric={metric} width={width} height={280} />
        )}
      </ParentSize>
    </div>
  );
}
