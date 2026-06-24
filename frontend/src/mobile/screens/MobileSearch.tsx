import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePlayerSearch } from '../../hooks';
import { initials, posLabel } from '../../utils/format';
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
    <div className="m-scroll">
      <div className="m-lb-head">
        <h1 className="m-lb-title">Search</h1>
        <div className="m-search">
          <svg className="ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <input placeholder="Search players" value={q} onChange={e => setQ(e.target.value)} autoFocus enterKeyHint="search" />
        </div>
      </div>

      <div className="m-lb-list">
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
                className="m-lb-row"
                style={{ ['--team-color' as string]: color }}
                onClick={() => navigate(`/player/${p.bbref_id}`)}
              >
                <div className="m-lb-rank" />
                <div className="m-lb-shot" style={{ background: color }}>{initials(name)}</div>
                <div className="m-lb-info">
                  <div className="m-lb-name">{name}</div>
                  <div className="m-lb-meta">
                    <span className="team-dot" style={{ background: color }} />
                    <span>{posLabel(p.primary_position, p.throws, false)}</span>
                    <span style={{ opacity: 0.5 }}>·</span>
                    <span>{years(p)}</span>
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
      <div className="m-scroll-pad" />
    </div>
  );
}
