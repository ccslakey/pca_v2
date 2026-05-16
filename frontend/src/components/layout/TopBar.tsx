import { Link } from "react-router-dom";
import { PlayerSearch } from "./PlayerSearch";
import { ThemePicker } from "./ThemePicker";
import { MAX_PLAYERS } from "../../constants";

interface Props {
  selectedIds: string[];
  onSelect: (id: string) => void;
  hideSearch?: boolean;
}

export function TopBar({ selectedIds, onSelect, hideSearch }: Props) {
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
      <Link to="/browse" className="topbar-browse-link">
        Browse Players
      </Link>
      {!hideSearch && (
        <PlayerSearch
          selectedIds={selectedIds}
          onSelect={onSelect}
          maxPlayers={MAX_PLAYERS}
        />
      )}
      <ThemePicker />
    </header>
  );
}
