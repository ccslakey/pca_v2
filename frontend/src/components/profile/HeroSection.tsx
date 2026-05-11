import { Link } from 'react-router-dom';
import type { ChartSeason } from '../../types';

interface Peak { season: number; val: number }

interface Props {
  player: {
    id: string;
    name: string;
    initials: string;
    pos: string;
    years: string;
    seasons: ChartSeason[];
  };
  color:     string;
  jerseyNum: number;
  peak:      Peak | null;
}

export function HeroSection({ player, color, jerseyNum, peak }: Props) {
  return (
    <div className="hero">
      <div className="hero-left">
        <div className="hero-headshot" style={{ background: color }}>
          {player.initials}
          <span className="hero-jersey">#{jerseyNum}</span>
        </div>
      </div>
      <div className="hero-mid">
        <div className="hero-eyebrow">
          <span className="swatch" style={{ background: color }} />
          {player.pos} · {player.years}
        </div>
        <h1 className="hero-name">{player.name}</h1>
        <div className="hero-meta">
          <span><span className="label">Pos</span> {player.pos}</span>
          <span className="sep">·</span>
          <span><span className="label">Active</span> {player.years}</span>
          <span className="sep">·</span>
          <span><span className="label">Seasons</span> {player.seasons.length}</span>
          {peak && (
            <>
              <span className="sep">·</span>
              <span><span className="label">Peak WAR</span> {peak.val.toFixed(1)} ({peak.season})</span>
            </>
          )}
        </div>
      </div>
      <div className="hero-right hero-actions">
        <Link to={`/?compare=${player.id}`} className="btn">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Compare
        </Link>
      </div>
    </div>
  );
}
