import { PlayerSearch } from './PlayerSearch';
import { MAX_PLAYERS } from '../constants';

interface Props {
  selectedIds: string[];
  onSelect: (id: string) => void;
}

export function TopBar({ selectedIds, onSelect }: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark" />
        <span className="brand-name">Career Arc Visualizer</span>
        <span className="topbar-meta">
          <span className="dot" />
          Baseball Reference
        </span>
      </div>
      <PlayerSearch
        selectedIds={selectedIds}
        onSelect={onSelect}
        maxPlayers={MAX_PLAYERS}
      />
    </header>
  );
}
