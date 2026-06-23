import { useNavigate } from 'react-router-dom';
import { useSavedPlayers } from '../hooks/useSavedPlayers';
import { playerColor } from '../../utils/color';
import { initials } from '../../utils/format';

export function MobileSaved() {
  const navigate = useNavigate();
  const { saved, remove } = useSavedPlayers();

  return (
    <div className="m-screen m-saved">
      <header className="m-screen-head">
        <h1 className="m-screen-title">Saved</h1>
        <span className="m-screen-count">{saved.length}</span>
      </header>

      <div className="m-list">
        {saved.length === 0 ? (
          <div className="m-empty">
            No saved players yet. Tap <strong>Follow</strong> on a player to add them here.
          </div>
        ) : (
          saved.map(p => {
            const color = playerColor(p.bbref_id);
            return (
              <div key={p.bbref_id} className="m-row">
                <button
                  className="m-row-tap"
                  onClick={() => navigate(`/player/${p.bbref_id}`)}
                >
                  <span className="m-swatch" style={{ background: color }}>
                    {initials(p.name)}
                  </span>
                  <span className="m-row-main">
                    <span className="m-row-name">{p.name}</span>
                    <span className="m-row-sub">{p.pos}</span>
                  </span>
                </button>
                <button
                  className="m-row-remove"
                  onClick={() => remove(p.bbref_id)}
                  aria-label={`Remove ${p.name}`}
                >
                  ✕
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
