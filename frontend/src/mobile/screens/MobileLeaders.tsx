import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLeaderboard } from '../../hooks';
import type { LeaderboardFilters, LeaderboardPlayer } from '../../types';
import { posLabel } from '../../utils/format';
import { playerColor } from '../../utils/color';

const POS_OPTIONS = ['All', 'P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH'];

const ERA_PRESETS = [
  { label: 'All eras', era_start: undefined, era_end: undefined },
  { label: 'Pre-1920', era_start: undefined, era_end: 1919 },
  { label: '1920–60', era_start: 1920, era_end: 1960 },
  { label: '1961–93', era_start: 1961, era_end: 1993 },
  { label: '1994–09', era_start: 1994, era_end: 2009 },
  { label: '2010+', era_start: 2010, era_end: undefined },
];

// Sort keys validated against the leaderboard serializer (see PlayerBrowser.tsx).
// OPS is intentionally absent — LeaderboardPlayer carries no OPS column.
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

function statFor(p: LeaderboardPlayer, sort: string): string {
  if (sort === 'peak_war') return `${p.peak_war.toFixed(1)} pk`;
  if (sort === 'career_hr') {
    if (p.is_pitcher) return p.career_era != null ? `${p.career_era.toFixed(2)} ERA` : '—';
    return p.career_hr != null ? `${p.career_hr} HR` : '—';
  }
  return `${p.career_war.toFixed(1)} WAR`;
}

export function MobileLeaders() {
  const navigate = useNavigate();
  const [pos, setPos] = useState('All');
  const [eraIdx, setEraIdx] = useState(0);
  const [sort, setSort] = useState<string>('career_war');

  const era = ERA_PRESETS[eraIdx];
  const filters: LeaderboardFilters = {
    pos: pos === 'All' ? undefined : pos,
    era_start: era.era_start,
    era_end: era.era_end,
    sort,
    order: 'desc',
    page: 1,
    page_size: 50,
  };

  const { data, isFetching } = useLeaderboard(filters);
  const players = data?.results ?? [];

  return (
    <div className="m-screen m-leaders">
      <header className="m-screen-head">
        <h1 className="m-screen-title">Leaders</h1>
        <span className="m-screen-count">
          {isFetching && !data ? '…' : `${(data?.count ?? 0).toLocaleString()}`}
        </span>
      </header>

      <div className="m-chiprow">
        {SORTS.map(s => (
          <button
            key={s.key}
            className={`m-chip ${sort === s.key ? 'is-active' : ''}`}
            onClick={() => setSort(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="m-chiprow m-chiprow-scroll">
        {POS_OPTIONS.map(o => (
          <button
            key={o}
            className={`m-chip ${pos === o ? 'is-active' : ''}`}
            onClick={() => setPos(o)}
          >
            {o}
          </button>
        ))}
      </div>

      <div className="m-chiprow m-chiprow-scroll">
        {ERA_PRESETS.map((ep, i) => (
          <button
            key={ep.label}
            className={`m-chip ${eraIdx === i ? 'is-active' : ''}`}
            onClick={() => setEraIdx(i)}
          >
            {ep.label}
          </button>
        ))}
      </div>

      <div className={`m-list ${isFetching && data ? 'is-refetching' : ''}`}>
        {players.map((p, i) => {
          const color = playerColor(p.bbref_id);
          return (
            <button
              key={p.bbref_id}
              className="m-row"
              onClick={() => navigate(`/player/${p.bbref_id}`)}
            >
              <span className="m-rank">{i + 1}</span>
              <span className="m-swatch" style={{ background: color }}>
                {(p.first_name[0] ?? '') + (p.last_name[0] ?? '')}
              </span>
              <span className="m-row-main">
                <span className="m-row-name">{p.first_name} {p.last_name}</span>
                <span className="m-row-sub">
                  {posLabel(p.primary_position, p.throws, p.is_pitcher)} · {years(p)}
                </span>
              </span>
              <span className="m-row-stat">{statFor(p, sort)}</span>
            </button>
          );
        })}
        {!isFetching && players.length === 0 && (
          <div className="m-empty">No players match these filters.</div>
        )}
      </div>
    </div>
  );
}
