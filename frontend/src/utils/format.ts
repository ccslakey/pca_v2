/** Convert primary_position + throws to a display label, e.g. "RHP", "LHP", "CF". */
export function posLabel(
  primaryPosition: string | null,
  throws: string | null,
  isPitcher: boolean,
): string {
  if (primaryPosition === 'P' || (isPitcher && !primaryPosition)) {
    if (throws === 'L') return 'LHP';
    if (throws === 'R') return 'RHP';
    return 'P';
  }
  return primaryPosition ?? (isPitcher ? 'P' : 'B');
}

export function initials(name: string): string {
  const parts = name.trim().split(' ');
  return parts.length >= 2
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}
