import "./styles/NarrativePanel.scss";
import { useState } from "react";
import { Sparkle, ShieldCheck, CaretRight } from "@phosphor-icons/react";
import { useNarrative } from "../../../hooks";
import { Skeleton } from "../../Skeleton";

interface Props {
  bbrefId: string;
}

const TOOL_LABELS: Record<string, string> = {
  get_career_totals: "career totals",
  get_season_log: "season log",
  get_awards: "awards",
  get_similar_players: "similar players",
  search_methodology: "methodology",
};

export function NarrativePanel({ bbrefId }: Props) {
  const { data, isLoading, isError } = useNarrative(bbrefId);
  const [showTrace, setShowTrace] = useState(false);

  // Nothing useful to show — hide the panel entirely rather than leave a husk.
  if (isError || (data && !data.text)) return null;

  const isLlm = data?.source === "llm";
  const trace = data?.trace;
  const tools = trace?.tool_calls ?? [];
  const hasTrace = isLlm && tools.length > 0;

  return (
    <div className="panel narrative-panel">
      <div className="panel-header">
        <div className="panel-title">
          Career summary
          {data && (
            <span
              className={`narrative-badge ${isLlm ? "is-ai" : "is-template"}`}
              title={
                isLlm
                  ? "Written by an AI agent from this player's own statistics. Every number is verified against the database before it's shown."
                  : "Generated deterministically from this player's statistics."
              }
            >
              {isLlm ? <Sparkle weight="fill" size={11} /> : null}
              {isLlm ? "AI summary" : "Auto summary"}
            </span>
          )}
        </div>
        {isLlm && (
          <span className="narrative-verified" title="Every figure traces to this player's stored stats.">
            <ShieldCheck weight="fill" size={13} /> verified
          </span>
        )}
      </div>

      {isLoading || !data ? (
        <div className="narrative-skeleton">
          <Skeleton variant="text" width="100%" />
          <Skeleton variant="text" width="92%" />
          <Skeleton variant="text" width="74%" />
        </div>
      ) : (
        <>
          <p className="narrative-text">{data.text}</p>

          {hasTrace && (
            <div className="narrative-trace">
              <button
                className="narrative-trace-toggle"
                onClick={() => setShowTrace((s) => !s)}
                aria-expanded={showTrace}
              >
                <CaretRight size={11} weight="bold" className={showTrace ? "open" : ""} />
                How this was generated
              </button>
              {showTrace && (
                <dl className="narrative-trace-body">
                  <div>
                    <dt>Retrieved</dt>
                    <dd>{tools.map((t) => TOOL_LABELS[t.name] ?? t.name).join(", ")}</dd>
                  </div>
                  <div>
                    <dt>Model calls</dt>
                    <dd>{trace?.model_calls ?? "—"}</dd>
                  </div>
                  {(trace?.repairs ?? 0) > 0 && (
                    <div>
                      <dt>Repairs</dt>
                      <dd>{trace?.repairs}</dd>
                    </div>
                  )}
                  <div>
                    <dt>Verification</dt>
                    <dd className="ok">passed</dd>
                  </div>
                  {data.model && (
                    <div>
                      <dt>Model</dt>
                      <dd className="mono">{data.model}</dd>
                    </div>
                  )}
                </dl>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
