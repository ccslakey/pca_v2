import "../components/profile/panel.scss";
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useChartPlayer,
  usePlayerBundle,
  useSimilarPlayers,
  usePlayerAwards,
  usePlayerDetail,
} from "../hooks";
import { METRICS } from "../constants";
import type { MetricId } from "../types";
import { peakSeason, careerWar, sumMetric } from "../utils/chart";
import { playerColor, colorTint } from "../utils/color";
import { HeroSection } from "../components/profile/panels/HeroSection";
import { StatGrid } from "../components/profile/panels/StatGrid";
import { CareerArcPanel } from "../components/profile/panels/CareerArcPanel";
import { SparklinePanel } from "../components/profile/panels/SparklinePanel";
import { SeasonLogPanel } from "../components/profile/panels/SeasonLogPanel";
import { NarrativePanel } from "../components/profile/panels/NarrativePanel";
import { SimilarPlayersPanel } from "../components/profile/panels/SimilarPlayersPanel";
import { AwardsPanel } from "../components/profile/panels/AwardsPanel";
import { JamesScoresPanel } from "../components/profile/panels/JamesScoresPanel";
import { PitchZone } from "../components/profile/charts/PitchZone";
import { ProfilePageSkeleton } from "../components/profile/ProfilePageSkeleton";
import { TopBar } from "../components/layout/TopBar";

export function ProfilePage() {
  const { bbrefId } = useParams<{ bbrefId: string }>();
  const [metric, setMetric] = useState<MetricId>("war");
  const [tab, setTab] = useState<"standard" | "advanced">("standard");

  const { data: player, isLoading } = useChartPlayer(bbrefId ?? null, 0);
  const { data: bundle } = usePlayerBundle(bbrefId ?? null);
  const { data: similar } = useSimilarPlayers(bbrefId ?? null);
  const { data: awards = [] } = usePlayerAwards(bbrefId ?? null);
  const { data: detail } = usePlayerDetail(bbrefId ?? null);

  if (isLoading || !player) {
    return <ProfilePageSkeleton />;
  }

  const color = playerColor(player.id);
  const cssVars = {
    "--team-color": color,
    "--team-tint": colorTint(color, 0.1),
    "--team-glow": colorTint(color, 0.22),
  } as React.CSSProperties;

  const war = careerWar(player.seasons);
  const peak = peakSeason(player.seasons, "war");
  const careerHR = sumMetric(player.seasons, "hr") ?? 0;
  const careerSO = sumMetric(player.seasons, "so") ?? 0;
  const careerAVG = sumMetric(player.seasons, "avg");
  const careerOPS = sumMetric(player.seasons, "ops");
  const careerERA = sumMetric(player.seasons, "era");
  const jerseyNum = (player.id.charCodeAt(0) % 60) + 1;

  const availableMetrics = METRICS.filter((m) => {
    if (m.id === "era") return player.isPitcher;
    if (["hr", "avg", "ops"].includes(m.id)) return player.isBatter;
    return true;
  });

  return (
    <div className="profile" style={cssVars}>
      <TopBar selectedIds={[]} onSelect={() => null} hideSearch={true} />

      <div className="profile-main">
        <HeroSection
          player={player}
          color={color}
          jerseyNum={jerseyNum}
          peak={peak}
        />
        <StatGrid
          player={player}
          war={war}
          peak={peak}
          careerHR={careerHR}
          careerSO={careerSO}
          careerAVG={careerAVG}
          careerOPS={careerOPS}
          careerERA={careerERA}
        />

        <div className="col-2">
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <NarrativePanel bbrefId={player.id} />
            <CareerArcPanel
              player={player}
              color={color}
              metric={metric}
              setMetric={setMetric}
              availableMetrics={availableMetrics}
            />
            <SparklinePanel
              player={player}
              color={color}
              availableMetrics={availableMetrics}
            />
            <SeasonLogPanel
              player={player}
              color={color}
              peak={peak}
              tab={tab}
              setTab={setTab}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {similar &&
              (similar.batters.length > 0 || similar.pitchers.length > 0) && (
                <SimilarPlayersPanel similar={similar} />
              )}

            {(player.isBatter || player.isPitcher) && (
              <div className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    Pitch zone
                    <span className="muted">Statcast 2015–present</span>
                  </div>
                </div>
                <PitchZone
                  bbrefId={player.id}
                  isBatter={player.isBatter}
                  isPitcher={player.isPitcher}
                  color={color}
                />
              </div>
            )}

            {detail?.james_score && (
              <JamesScoresPanel
                james={detail.james_score}
                isBatter={player.isBatter}
                isPitcher={player.isPitcher}
              />
            )}

            <AwardsPanel awards={awards} color={color} />
          </div>
        </div>

        <p className="footer-note">
          Data: Baseball Reference · All WAR values are bWAR
          {bundle?.last_updated ? ` · Updated ${bundle.last_updated}` : ""}
          {" · "}
          <a href="/methodology" style={{ color: "inherit", opacity: 0.7 }}>
            Methodology
          </a>
        </p>
      </div>
    </div>
  );
}
