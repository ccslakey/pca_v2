import "./PlayerCard.scss";
import { Link } from "react-router-dom";
import type { ChartPlayer, MetricId } from "../../types";
import { METRICS } from "../../constants";
import { peakSeason, careerWar, fmtMetric } from "../../utils/chart";
import { fmtPercentile } from "../../utils/format";

interface Props {
  player: ChartPlayer;
  metric: MetricId;
  isHovered: boolean;
  onHoverEnter: () => void;
  onHoverLeave: () => void;
  onRemove: () => void;
}

const XIcon = ({ size = 11 }: { size?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.5"
  >
    <line x1="6" y1="6" x2="18" y2="18" />
    <line x1="18" y1="6" x2="6" y2="18" />
  </svg>
);

export function PlayerCard({
  player,
  metric,
  isHovered,
  onHoverEnter,
  onHoverLeave,
  onRemove,
}: Props) {
  const war = careerWar(player.seasons);
  const peak = peakSeason(player.seasons, metric);
  const metricLabel =
    METRICS.find((m) => m.id === metric)?.label ?? metric.toUpperCase();

  return (
    <Link
      to={`/player/${player.id}`}
      className={`player-card ${isHovered ? "is-hover" : ""}`}
      onMouseEnter={onHoverEnter}
      onMouseLeave={onHoverLeave}
      style={{ color: "inherit", textDecoration: "none" }}
    >
      <div className="accent-bar" style={{ background: player.color }} />
      <div className="player-card-head">
        <div className="head-shot" style={{ background: player.color }}>
          {player.initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            className="player-card-name"
            style={{
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {player.name}
          </div>
          <div className="player-card-meta">
            {player.pos} · {player.years}
          </div>
        </div>
        <button
          className="chip-x"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onRemove();
          }}
          title="Remove from comparison"
        >
          <XIcon size={16} />
        </button>
      </div>
      <div className="player-card-stats">
        <div className="stat">
          <div className="stat-label">Career WAR</div>
          <div className="stat-value">{war.toFixed(1)}</div>
          {player.warPercentile && (
            <div
              className="stat-sub"
              title={
                player.warPercentile.rank != null
                  ? `#${player.warPercentile.rank} of ${player.warPercentile.n} ${player.warPercentile.position} by career WAR`
                  : undefined
              }
            >
              {fmtPercentile(player.warPercentile.topPct)}{" "}
              {player.warPercentile.position}
            </div>
          )}
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
            <div className="stat-value" style={{ color: "var(--text-3)" }}>
              —
            </div>
          </div>
        )}
      </div>
    </Link>
  );
}
