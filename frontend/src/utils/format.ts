/** Convert primary_position + throws to a display label, e.g. "RHP", "LHP", "CF". */
export function posLabel(
  primaryPosition: string | null,
  throws: string | null,
  isPitcher: boolean,
): string {
  if (primaryPosition === "P" || (isPitcher && !primaryPosition)) {
    if (throws === "L") return "LHP";
    if (throws === "R") return "RHP";
    return "P";
  }
  return primaryPosition ?? (isPitcher ? "P" : "B");
}

/** Format a war_percentile as "top 3.2%" or "top 24%" depending on magnitude. */
export function fmtPercentile(topPct: number): string {
  if (topPct < 0.1) return "top <0.1%"; // toFixed(1) would show "0.0"
  return topPct <= 10
    ? `top ${topPct.toFixed(1)}%`
    : `top ${Math.round(topPct)}%`;
}

export function initials(name: string): string {
  const parts = name.trim().split(" ");
  return parts.length >= 2
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}
