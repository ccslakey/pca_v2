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

export function fmtPercentile(topPct: number): string {
  if (topPct < 0.1) return "top <0.1%";
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
