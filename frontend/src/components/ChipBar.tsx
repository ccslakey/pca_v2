import type { ChartPlayer } from '../types';
import { MAX_PLAYERS } from '../constants';

interface Props {
  players: ChartPlayer[];
  hoverPlayerId: string | null;
  setHoverPlayerId: (id: string | null) => void;
  onRemove: (id: string) => void;
}

const XIcon = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" />
  </svg>
);

const PlusIcon = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

export function ChipBar({ players, hoverPlayerId, setHoverPlayerId, onRemove }: Props) {
  return (
    <div className="chip-bar">
      <span className="chip-bar-label">Comparing</span>
      {players.map(p => (
        <span
          key={p.id}
          className="chip"
          style={{ borderColor: hoverPlayerId === p.id ? p.color + '88' : undefined }}
          onMouseEnter={() => setHoverPlayerId(p.id)}
          onMouseLeave={() => setHoverPlayerId(null)}
        >
          <span className="chip-swatch" style={{ background: p.color }} />
          <span className="chip-name">{p.name}</span>
          <span className="chip-meta">{p.pos}</span>
          <button className="chip-x" onClick={() => onRemove(p.id)} title="Remove">
            <XIcon />
          </button>
        </span>
      ))}
      {players.length < MAX_PLAYERS && (
        <span className="chip chip-add">
          <PlusIcon />
          Add player
        </span>
      )}
      <div style={{ flex: 1 }} />
      <span style={{ color: 'var(--text-3)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
        {players.length} / {MAX_PLAYERS}
      </span>
    </div>
  );
}
