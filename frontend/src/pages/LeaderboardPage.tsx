import { Link } from 'react-router-dom';
import { PlayerBrowser } from '../components/PlayerBrowser';
import './LeaderboardPage.scss';

export function LeaderboardPage() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <Link to="/" className="brand-back">← Compare</Link>
          <span className="brand-sep" />
          <span className="brand-name">Career Arc Visualizer</span>
        </div>
      </header>

      <div className="main leaderboard-main">
        <PlayerBrowser standalone />
      </div>
    </div>
  );
}
