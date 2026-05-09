import { useState, useEffect, useRef, useMemo } from 'react';
import { usePlayerSearch } from '../hooks';
import type { PlayerSummary } from '../types';

interface Props {
  selectedIds: string[];
  onSelect: (id: string) => void;
  maxPlayers: number;
}

function headshot(p: PlayerSummary) {
  return `${p.first_name[0] ?? ''}${p.last_name[0] ?? ''}`.toUpperCase();
}

function headshotColor(bbrefId: string) {
  // deterministic color from bbref_id
  let h = 0;
  for (const c of bbrefId) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  const hue = h % 360;
  return `oklch(0.72 0.18 ${hue})`;
}

export function PlayerSearch({ selectedIds, onSelect, maxPlayers }: Props) {
  const [q, setQ]               = useState('');
  const [open, setOpen]         = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);

  const wrapRef  = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data } = usePlayerSearch(q);
  const results: PlayerSummary[] = useMemo(() => data?.results ?? [], [data]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ⌘K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  function pick(p: PlayerSummary) {
    if (selectedIds.includes(p.bbref_id) || selectedIds.length >= maxPlayers) return;
    onSelect(p.bbref_id);
    setQ('');
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || !results.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(i => Math.min(results.length - 1, i + 1)); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setActiveIdx(i => Math.max(0, i - 1)); }
    if (e.key === 'Enter')     { const p = results[activeIdx]; if (p) pick(p); }
    if (e.key === 'Escape')    setOpen(false);
  }

  return (
    <div className="search" ref={wrapRef}>
      <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" />
      </svg>
      <input
        ref={inputRef}
        className="search-input"
        placeholder="Search players…"
        value={q}
        onChange={e => { setQ(e.target.value); setActiveIdx(0); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {!q && <span className="search-kbd">⌘K</span>}
      {open && (
        <div className="search-dropdown">
          <div className="search-section-title">
            {q ? `Results (${results.length})` : 'Type to search players'}
          </div>
          {q && results.length === 0 && (
            <div className="search-empty">No players match "{q}"</div>
          )}
          {results.map((p, i) => {
            const taken = selectedIds.includes(p.bbref_id);
            const years = p.mlb_played_first
              ? `${p.mlb_played_first}–${p.mlb_played_last ?? 'present'}`
              : '';
            return (
              <div
                key={p.bbref_id}
                className={`search-result ${i === activeIdx ? 'is-active' : ''} ${taken ? 'is-disabled' : ''}`}
                onMouseEnter={() => setActiveIdx(i)}
                onMouseDown={e => { e.preventDefault(); if (!taken) pick(p); }}
              >
                <div className="search-headshot" style={{ background: headshotColor(p.bbref_id) }}>
                  {headshot(p)}
                </div>
                <div className="search-result-info">
                  <div className="search-result-name">{p.first_name} {p.last_name}</div>
                  <div className="search-result-meta">{p.bbref_id}{years ? ` · ${years}` : ''}</div>
                </div>
                {taken && (
                  <span style={{ color: 'var(--text-3)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
                    added
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
