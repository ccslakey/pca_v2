import "./MetricToggle.scss";
import { METRICS } from "../../constants";
import type { MetricId } from "../../types";
import { AnnotationGlyph } from "../AnnotationGlyph";

interface Props {
  metric: MetricId;
  onChange: (m: MetricId) => void;
}

export function MetricToggle({ metric, onChange }: Props) {
  return (
    <div className="metric-row">
      <div className="metric-toggle" role="tablist">
        {METRICS.map((m) => (
          <button
            key={m.id}
            role="tab"
            aria-selected={metric === m.id}
            className={`metric-pill ${metric === m.id ? "is-active" : ""}`}
            onClick={() => onChange(m.id)}
          >
            {m.label}
            {metric === m.id && <span className="full">· {m.full}</span>}
          </button>
        ))}
      </div>

      <div className="metric-meta">
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
      </div>
    </div>
  );
}
