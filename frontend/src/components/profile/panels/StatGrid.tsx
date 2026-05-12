import "./styles/StatGrid.scss";
import { fmtMetric } from "../../../utils/chart";

interface Peak {
  season: number;
  val: number;
}

interface Props {
  player: {
    isBatter: boolean;
    isPitcher: boolean;
    seasons: { length: number };
  };
  war: number;
  peak: Peak | null;
  careerHR: number;
  careerSO: number;
  careerAVG: number | null;
  careerOPS: number | null;
  careerERA: number | null;
}

export function StatGrid({
  player,
  war,
  peak,
  careerHR,
  careerSO,
  careerAVG,
  careerOPS,
  careerERA,
}: Props) {
  const isPureP = player.isPitcher && !player.isBatter;
  return (
    <div className="stat-grid">
      <div className="stat-block is-headline">
        <div className="stat-label">Career WAR</div>
        <div className="stat-value">{war.toFixed(1)}</div>
        {peak && (
          <div className="stat-sub">
            Peak {peak.val.toFixed(1)} in {peak.season}
          </div>
        )}
      </div>
      {player.isBatter && (
        <div className="stat-block">
          <div className="stat-label">Home Runs</div>
          <div className="stat-value">{careerHR}</div>
          <div className="stat-sub">
            {(careerHR / player.seasons.length).toFixed(1)} / yr
          </div>
        </div>
      )}
      {player.isBatter && (
        <div className="stat-block">
          <div className="stat-label">AVG / OPS</div>
          <div className="stat-value">{fmtMetric("avg", careerAVG)}</div>
          <div className="stat-sub">OPS {fmtMetric("ops", careerOPS)}</div>
        </div>
      )}
      {player.isPitcher && (
        <div className="stat-block">
          <div className="stat-label">ERA</div>
          <div className="stat-value">{fmtMetric("era", careerERA)}</div>
          <div className="stat-sub">{careerSO} K career</div>
        </div>
      )}
      <div className="stat-block">
        <div className="stat-label">{isPureP ? "Strikeouts" : "Career SO"}</div>
        <div className="stat-value">{careerSO}</div>
        <div className="stat-sub">
          {player.seasons.length > 0
            ? (careerSO / player.seasons.length).toFixed(0)
            : "—"}{" "}
          / yr
        </div>
      </div>
    </div>
  );
}
