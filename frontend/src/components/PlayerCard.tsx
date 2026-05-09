import { Link } from 'react-router-dom';
import type { ChartPlayer, MetricId } from '../types';
import { METRICS } from '../constants';
import { peakSeason, careerWar, fmtMetric } from '../utils/chart';

interface Props {
  player: ChartPlayer;
  metric: MetricId;
  isHovered: boolean;
  onHoverEnter: () => void;
  onHoverLeave: () => void;
  onRemove: () => void;
}

const XIcon = () => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" />
  </svg>
);

export function PlayerCard({ player, metric, isHovered, onHoverEnter, onHoverLeave, onRemove }: Props) {
  const war  = careerWar(player.seasons);
  const peak = peakSeason(player.seasons, metric);
  const metricLabel = METRICS.find(m => m.id === metric)?.label ?? metric.toUpperCase();

  return (
    <div
      className={`player-card ${isHovered ? 'is-hover' : ''}`}
      onMouseEnter={onHoverEnter}
      onMouseLeave={onHoverLeave}
    >
      <div className="accent-bar" style={{ background: player.color }} />
      <div className="player-card-head">
        <div className="head-shot" style={{ background: player.color }}>
          {player.initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Link
            to={`/player/${player.id}`}
            className="player-card-name"
            style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'inherit', textDecoration: 'none' }}
          >
            {player.name}
          </Link>
          <div className="player-card-meta">{player.pos} · {player.years}</div>
        </div>
        <button className="chip-x" onClick={onRemove} title="Remove from comparison">
          <XIcon />
        </button>
      </div>
      <div className="player-card-stats">
        <div className="stat">
          <div className="stat-label">Career WAR</div>
          <div className="stat-value">{war.toFixed(1)}</div>
        </div>
        {peak && (
          <div className="stat">
            <div className="stat-label">Peak {metricLabel}</div>
            <div className="stat-value">
              {fmtMetric(metric, peak.val)}
              <span className="sub">'{String(peak.season).slice(2)}</span>
            </div>
          </div>
        )}
        {!peak && (
          <div className="stat">
            <div className="stat-label">Peak {metricLabel}</div>
            <div className="stat-value" style={{ color: 'var(--text-3)' }}>—</div>
          </div>
        )}
      </div>
    </div>
  );
}
