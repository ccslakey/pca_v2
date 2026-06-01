import "./MetricToggle.scss";
import { METRICS } from "../../constants";
import type { MetricId, XMode } from "../../types";
import { AnnotationGlyph } from "../AnnotationGlyph";
import { MetricExplainer } from "../MetricExplainer";

interface Props {
  metric: MetricId;
  onChange: (m: MetricId) => void;
  xMode: XMode;
  onXModeChange: (m: XMode) => void;
  showGlyphs: boolean;
  onToggleGlyphs: () => void;
}

export function MetricToggle({
  metric,
  onChange,
  xMode,
  onXModeChange,
  showGlyphs,
  onToggleGlyphs,
}: Props) {
  return (
    <div className="metric-row">
      <div className="metric-toggle" role="tablist">
        {METRICS.map((m) => (
          <button
            key={m.id}
            role="tab"
            aria-label={m.label}
            aria-selected={metric === m.id}
            className={`metric-pill ${metric === m.id ? "is-active" : ""}`}
            onClick={() => onChange(m.id)}
          >
            {m.label}
            {metric === m.id && <span className="full">· {m.full}</span>}
          </button>
        ))}
      </div>

      <div className="xmode-toggle" role="tablist" aria-label="X-axis mode">
        <button
          role="tab"
          aria-selected={xMode === "year"}
          className={`xmode-pill ${xMode === "year" ? "is-active" : ""}`}
          onClick={() => onXModeChange("year")}
        >
          Calendar
        </button>
        <button
          role="tab"
          aria-selected={xMode === "age"}
          className={`xmode-pill ${xMode === "age" ? "is-active" : ""}`}
          onClick={() => onXModeChange("age")}
        >
          By Age
        </button>
      </div>

      <div className="metric-meta">
        <MetricExplainer metric={metric} />
        <button
          className={`glyph-toggle ${showGlyphs ? "is-active" : ""}`}
          onClick={onToggleGlyphs}
          title={showGlyphs ? "Hide award icons" : "Show award icons"}
        >
          Awards
        </button>
        <span className={`glyph-legend ${showGlyphs ? "" : "is-hidden"}`}>
          {(
            [
              { kind: "mvp", label: "MVP" },
              { kind: "cy", label: "Cy Young" },
              { kind: "gg", label: "Gold Glove" },
              { kind: "asg", label: "All-Star" },
              { kind: "ws", label: "World Series" },
            ] as const
          ).map(({ kind, label }) => (
            <span key={kind} className="key">
              <AnnotationGlyph kind={kind} color="#f5f7fb" size={12} />
              {label}
            </span>
          ))}
        </span>
      </div>
    </div>
  );
}
