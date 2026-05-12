import "./styles/SeasonLogPanel.scss";
import { fmtMetric } from "../../../utils/chart";
import type { ChartPlayer } from "../../../types";

interface Peak {
  season: number;
  val: number;
}

interface Props {
  player: ChartPlayer;
  color: string;
  peak: Peak | null;
  tab: "standard" | "advanced";
  setTab: (t: "standard" | "advanced") => void;
}

export function SeasonLogPanel({ player, color, peak, tab, setTab }: Props) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          Season log
          <span className="muted">{player.seasons.length} seasons</span>
        </div>
        <div className="tabs">
          <button
            className={`tab ${tab === "standard" ? "is-active" : ""}`}
            onClick={() => setTab("standard")}
          >
            Standard
          </button>
          <button
            className={`tab ${tab === "advanced" ? "is-active" : ""}`}
            onClick={() => setTab("advanced")}
          >
            Advanced
          </button>
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="season-table">
          <thead>
            <tr>
              <th className="year-col">Year</th>
              <th>WAR</th>
              {player.isBatter && <th>AVG</th>}
              {player.isBatter && <th>HR</th>}
              {player.isBatter && <th>OPS</th>}
              {player.isPitcher && <th>ERA</th>}
              {player.isPitcher && <th>SO</th>}
            </tr>
          </thead>
          <tbody>
            {[...player.seasons].reverse().map((s) => {
              const isPeak = peak?.season === s.season;
              const warWidth = Math.max(
                2,
                Math.min(80, ((s.war ?? 0) / 10) * 80),
              );
              return (
                <tr key={s.season} className={isPeak ? "is-peak" : ""}>
                  <td>{s.season}</td>
                  <td>
                    <span
                      className="micro-bar"
                      style={{ width: warWidth, background: color }}
                    />
                    {fmtMetric("war", s.war)}
                  </td>
                  {player.isBatter && <td>{fmtMetric("avg", s.avg)}</td>}
                  {player.isBatter && <td>{s.hr ?? "—"}</td>}
                  {player.isBatter && <td>{fmtMetric("ops", s.ops)}</td>}
                  {player.isPitcher && <td>{fmtMetric("era", s.era)}</td>}
                  {player.isPitcher && <td>{s.so ?? "—"}</td>}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
