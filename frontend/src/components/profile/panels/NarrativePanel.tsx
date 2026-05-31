import "./styles/NarrativePanel.scss";
import { useNarrative } from "../../../hooks";
import { Skeleton } from "../../Skeleton";

interface Props {
  bbrefId: string;
}

export function NarrativePanel({ bbrefId }: Props) {
  const { data, isLoading, isError } = useNarrative(bbrefId);

  // Nothing useful to show — hide the panel entirely rather than leave a husk.
  if (isError || (data && !data.text)) return null;

  const label =
    data?.source === "llm" ? "AI summary" : "Career summary";

  return (
    <div className="panel narrative-panel">
      <div className="panel-header">
        <div className="panel-title">
          {label}
          <span className="muted">grounded in this player's stats</span>
        </div>
      </div>

      {isLoading || !data ? (
        <div className="narrative-skeleton">
          <Skeleton variant="text" width="100%" />
          <Skeleton variant="text" width="92%" />
          <Skeleton variant="text" width="74%" />
        </div>
      ) : (
        <p className="narrative-text">{data.text}</p>
      )}
    </div>
  );
}
