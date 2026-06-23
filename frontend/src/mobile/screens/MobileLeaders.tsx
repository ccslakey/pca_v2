import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLeaderboard } from '../../hooks';
import type { LeaderboardFilters, LeaderboardPlayer } from '../../types';
import { initials, posLabel } from '../../utils/format';
import { playerColor } from '../../utils/color';

const POSITIONS = ['All', 'P', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'C'];

// Sort keys validated against the leaderboard serializer (see PlayerBrowser.tsx).
// OPS is omitted vs the comp — LeaderboardPlayer carries no OPS column.
const SORTS = [
  { key: 'career_war', label: 'WAR' },
  { key: 'peak_war', label: 'Peak' },
  { key: 'career_hr', label: 'HR' },
] as const;

function years(p: LeaderboardPlayer): string {
  const d = p.debut ? new Date(p.debut).getUTCFullYear() : null;
  const f = p.final_game ? new Date(p.final_game).getUTCFullYear() : null;
  if (d && f) return `${d}–${f}`;
  return d ? `${d}–` : '—';
}

function statFor(p: LeaderboardPlayer, sort: string): { v: string; l: string } {
  if (sort === 'peak_war') return { v: p.peak_war.toFixed(1), l: 'Peak' };
  if (sort === 'career_hr') {
    if (p.is_pitcher) return { v: p.career_era != null ? p.career_era.toFixed(2) : '—', l: 'ERA' };
    return { v: p.career_hr != null ? String(p.career_hr) : '—', l: 'HR' };
  }
  return { v: p.career_war.toFixed(1), l: 'WAR' };
}

export function MobileLeaders() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [pos, setPos] = useState('All');
  const [sort, setSort] = useState<string>('career_war');

  const filters: LeaderboardFilters = {
    pos: pos === 'All' ? undefined : pos === 'P' ? 'P' : pos,
    sort,
    order: 'desc',
    page: 1,
    page_size: 50,
  };
  const { data, isFetching } = useLeaderboard(filters);

  const rows = useMemo(() => {
    let r = data?.results ?? [];
    const needle = q.trim().toLowerCase();
    if (needle) {
      r = r.filter(p => `${p.first_name} ${p.last_name}`.toLowerCase().includes(needle));
    }
    return r.slice(0, 24);
  }, [data, q]);

  return (
    <div className="m-scroll">
      <div className="m-lb-head">
        <h1 className="m-lb-title">
          Leaders
          <span className="muted">
            {isFetching && !data ? '…' : `${rows.length} players`}
          </span>
        </h1>
        <div className="m-search">
          <svg className="ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <input placeholder="Search players" value={q} onChange={e => setQ(e.target.value)} />
        </div>
      </div>

      <div className="m-chips">
        <span className="m-chip" style={{ borderStyle: 'dashed', background: 'transparent' }}>
          <span className="lbl-key">Sort</span>
        </span>
        {SORTS.map(s => (
          <button key={s.key} className={`m-chip ${sort === s.key ? 'is-active' : ''}`} onClick={() => setSort(s.key)}>
            {s.label}
          </button>
        ))}
      </div>
      <div className="m-chips">
        <span className="m-chip" style={{ borderStyle: 'dashed', background: 'transparent' }}>
          <span className="lbl-key">Pos</span>
        </span>
        {POSITIONS.map(p => (
          <button key={p} className={`m-chip ${pos === p ? 'is-active' : ''}`} onClick={() => setPos(p)}>
            {p}
          </button>
        ))}
      </div>

      <div className="m-lb-list">
        {rows.map((p, i) => {
          const color = playerColor(p.bbref_id);
          const stat = statFor(p, sort);
          return (
            <button
              key={p.bbref_id}
              className="m-lb-row"
              style={{ ['--team-color' as string]: color }}
              onClick={() => navigate(`/player/${p.bbref_id}`)}
            >
              <div className="m-lb-rank">{i + 1}</div>
              <div className="m-lb-shot" style={{ background: color }}>
                {initials(`${p.first_name} ${p.last_name}`)}
              </div>
              <div className="m-lb-info">
                <div className="m-lb-name">{p.first_name} {p.last_name}</div>
                <div className="m-lb-meta">
                  <span className="team-dot" style={{ background: color }} />
                  <span>{posLabel(p.primary_position, p.throws, p.is_pitcher)}</span>
                  <span style={{ opacity: 0.5 }}>·</span>
                  <span>{years(p)}</span>
                </div>
              </div>
              <div className="m-lb-stat">
                <div className="v">{stat.v}</div>
                <div className="l">{stat.l}</div>
              </div>
            </button>
          );
        })}
        {!isFetching && rows.length === 0 && <div className="m-empty">No players match.</div>}
      </div>
      <div className="m-scroll-pad" />
    </div>
  );
}
