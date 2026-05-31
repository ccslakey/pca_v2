import "./MetricExplainer.scss";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Info, ArrowRight } from "@phosphor-icons/react";
import { useMethodologySearch } from "../hooks";
import { METRIC_QUERIES } from "../constants";
import { Skeleton } from "./Skeleton";
import type { MetricId } from "../types";

/** Inline "?" affordance that retrieves the methodology doc explaining a metric
 *  (semantic search over the docs). Renders nothing for metrics we don't document. */
export function MetricExplainer({ metric }: { metric: MetricId }) {
  const query = METRIC_QUERIES[metric] ?? null;
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  // Only fetch once the popover is opened.
  const { data, isLoading } = useMethodologySearch(open ? query : null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  if (!query) return null;
  const top = data?.results?.[0];

  return (
    <span className="metric-explainer" ref={ref}>
      <button
        className="metric-explainer-btn"
        aria-label="What does this metric mean?"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Info size={14} weight="bold" />
      </button>

      {open && (
        <div className="metric-explainer-pop" role="dialog">
          {isLoading || !data ? (
            <div className="mx-skeleton">
              <Skeleton variant="text" width="55%" />
              <Skeleton variant="text" width="100%" />
              <Skeleton variant="text" width="88%" />
            </div>
          ) : top ? (
            <>
              <div className="mx-title">{top.title}</div>
              <p className="mx-body">{cleanText(top.content, 320)}</p>
              <Link to={`/methodology/${top.slug}`} className="mx-link" onClick={() => setOpen(false)}>
                Read the full methodology <ArrowRight size={11} weight="bold" />
              </Link>
              <div className="mx-attr">retrieved from methodology · {Math.round(top.score * 100)}% match</div>
            </>
          ) : (
            <p className="mx-empty">Explanation unavailable.</p>
          )}
        </div>
      )}
    </span>
  );
}

/** Strip light markdown and collapse whitespace for a clean popover snippet. */
function cleanText(s: string, max: number): string {
  const clean = s
    .replace(/`{1,3}([^`]*)`{1,3}/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/^#+\s*/gm, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
  return clean.length > max ? clean.slice(0, max).trimEnd() + "…" : clean;
}
