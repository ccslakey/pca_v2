import { useNavigate } from 'react-router-dom';
import { useSavedPlayers } from '../hooks/useSavedPlayers';
import { playerColor } from '../../utils/color';
import { initials } from '../../utils/format';

export function MobileSaved() {
  const navigate = useNavigate();
  const { saved, remove } = useSavedPlayers();

  return (
    <div className="m-scroll">
      <div className="m-lb-head">
        <h1 className="m-lb-title">
          Saved
          <span className="muted">{saved.length} {saved.length === 1 ? 'player' : 'players'}</span>
        </h1>
      </div>

      <div className="m-lb-list">
        {saved.length === 0 ? (
          <div className="m-empty">
            No saved players yet. Tap <strong>Follow</strong> on a player to add them here.
          </div>
        ) : (
          saved.map(p => {
            const color = playerColor(p.bbref_id);
            return (
              <div
                key={p.bbref_id}
                className="m-lb-row"
                style={{ ['--team-color' as string]: color, cursor: 'pointer' }}
                onClick={() => navigate(`/player/${p.bbref_id}`)}
              >
                <div className="m-lb-rank">★</div>
                <div className="m-lb-shot" style={{ background: color }}>{initials(p.name)}</div>
                <div className="m-lb-info">
                  <div className="m-lb-name">{p.name}</div>
                  <div className="m-lb-meta">
                    <span className="team-dot" style={{ background: color }} />
                    <span>{p.pos}</span>
                  </div>
                </div>
                <button
                  className="m-sheet-close"
                  aria-label={`Remove ${p.name}`}
                  onClick={e => { e.stopPropagation(); remove(p.bbref_id); }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M6 6l12 12M18 6l-12 12" /></svg>
                </button>
              </div>
            );
          })
        )}
      </div>
      <div className="m-scroll-pad" />
    </div>
  );
}
