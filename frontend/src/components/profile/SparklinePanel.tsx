import { Sparkline } from '../Sparkline';
import { fmtMetric, sumMetric, peakSeason } from '../../utils/chart';
import type { ChartPlayer, Metric } from '../../types';

interface Props {
  player:           ChartPlayer;
  color:            string;
  availableMetrics: Metric[];
}

export function SparklinePanel({ player, color, availableMetrics }: Props) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          By the numbers
          <span className="muted">all metrics, season by season</span>
        </div>
        {player.seasons[0] && (
          <div className="panel-action">since {player.seasons[0].season}</div>
        )}
      </div>
      <div className="spark-grid">
        {availableMetrics.map(m => {
          const series = player.seasons
            .map(s => s[m.id])
            .filter((v): v is number => v != null);
          if (!series.length) return null;
          const total = sumMetric(player.seasons, m.id);
          const pk    = peakSeason(player.seasons, m.id);
          return (
            <div key={m.id} className="spark">
              <div className="spark-head">
                <span className="spark-label">{m.label} · {m.full}</span>
                <span className="spark-value">
                  {fmtMetric(m.id, total)}
                  {pk && (
                    <span className="spark-sub">
                      {['war', 'hr', 'so'].includes(m.id) ? 'career' : 'career avg'}
                      {' · '}peak {fmtMetric(m.id, pk.val)} '{String(pk.season).slice(2)}
                    </span>
                  )}
                </span>
              </div>
              <Sparkline data={series} color={color} invert={m.id === 'era'} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
