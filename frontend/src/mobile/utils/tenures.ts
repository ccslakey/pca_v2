import type { BattingSeason, PitchingSeason } from '../../types';

export interface Tenure {
  team: string;
  startYear: number;
  endYear: number;
  color: string;
}

/** Deterministic oklch color from a team abbreviation — same hash shape as
 *  utils/color.ts playerColor, keyed on the team string instead of bbref_id. */
export function teamColor(team: string): string {
  let h = 0;
  for (const c of team) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return `oklch(0.70 0.15 ${h % 360})`;
}

/**
 * Group a player's batting + pitching seasons into consecutive team tenures.
 * `team` lives on BattingSeason/PitchingSeason but is dropped by mergeSeasons,
 * so this is the one bit of profile data not already on ChartSeason.
 */
export function deriveTenures(
  batting: BattingSeason[],
  pitching: PitchingSeason[],
): Tenure[] {
  // One team per year — prefer the stint with the most games when a year has
  // multiple rows (trades). Pitching rows count for pitchers; batting otherwise.
  const byYear = new Map<number, { team: string; games: number }>();

  const consider = (year: number, team: string | null, games: number | null) => {
    if (!team) return;
    const g = games ?? 0;
    const cur = byYear.get(year);
    if (!cur || g > cur.games) byYear.set(year, { team, games: g });
  };

  for (const s of batting) consider(s.year, s.team, s.games);
  for (const s of pitching) consider(s.year, s.team, s.games);

  const years = [...byYear.keys()].sort((a, b) => a - b);

  const tenures: Tenure[] = [];
  for (const y of years) {
    const team = byYear.get(y)!.team;
    const last = tenures[tenures.length - 1];
    if (last && last.team === team && y === last.endYear + 1) {
      last.endYear = y;
    } else {
      tenures.push({ team, startYear: y, endYear: y, color: teamColor(team) });
    }
  }
  return tenures;
}
