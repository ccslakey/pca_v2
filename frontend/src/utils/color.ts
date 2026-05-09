/** Deterministic oklch color from a bbref_id string. */
export function playerColor(bbrefId: string): string {
  let h = 0;
  for (const c of bbrefId) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return `oklch(0.72 0.18 ${h % 360})`;
}

/** CSS color-mix tint at a given opacity. */
export function colorTint(color: string, alpha: number): string {
  return `color-mix(in oklch, ${color} ${Math.round(alpha * 100)}%, transparent)`;
}
