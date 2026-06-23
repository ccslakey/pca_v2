import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePlayerSearch } from '../../hooks';
import { posLabel } from '../../utils/format';
import { playerColor } from '../../utils/color';
import type { PlayerSummary } from '../../types';

function years(p: PlayerSummary): string {
  const d = p.debut ? new Date(p.debut).getUTCFullYear() : null;
  const f = p.final_game ? new Date(p.final_game).getUTCFullYear() : null;
  if (d && f) return `${d}–${f}`;
  return d ? `${d}–` : '—';
}

export function MobileSearch() {
  const [q, setQ] = useState('');
  const navigate = useNavigate();
  const { data, isFetching } = usePlayerSearch(q.trim());
  const results = data?.results ?? [];

  return (
    <div className="m-screen m-search">
      <div className="m-search-bar">
        <input
          className="m-search-input"
          placeholder="Search players…"
          value={q}
          onChange={e => setQ(e.target.value)}
          autoFocus
          enterKeyHint="search"
        />
        {q && (
          <button className="m-search-clear" onClick={() => setQ('')} aria-label="Clear">✕</button>
        )}
      </div>

      <div className="m-list">
        {q.trim().length === 0 ? (
          <div className="m-empty">Type a name to find a player.</div>
        ) : isFetching && results.length === 0 ? (
          <div className="m-empty">Searching…</div>
        ) : results.length === 0 ? (
          <div className="m-empty">No players match “{q}”.</div>
        ) : (
          results.map(p => {
            const name = `${p.first_name} ${p.last_name}`;
            const color = playerColor(p.bbref_id);
            return (
              <button
                key={p.bbref_id}
                className="m-row"
                onClick={() => navigate(`/player/${p.bbref_id}`)}
              >
                <span className="m-swatch" style={{ background: color }}>
                  {(p.first_name[0] ?? '') + (p.last_name[0] ?? '')}
                </span>
                <span className="m-row-main">
                  <span className="m-row-name">{name}</span>
                  <span className="m-row-sub">
                    {posLabel(p.primary_position, p.throws, false)} · {years(p)}
                  </span>
                </span>
                <span className="m-row-chev">›</span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
