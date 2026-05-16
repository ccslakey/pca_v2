import { Link } from "react-router-dom";
import { PlayerBrowser } from "../components/PlayerBrowser";
import "../styles/LeaderboardPage.scss";
import { TopBar } from "../components/layout/TopBar";

export function LeaderboardPage() {
  return (
    <div className="app">
      <TopBar selectedIds={[]} onSelect={() => null} hideSearch={true} />

      <div className="main leaderboard-main">
        <PlayerBrowser standalone />
      </div>
    </div>
  );
}
