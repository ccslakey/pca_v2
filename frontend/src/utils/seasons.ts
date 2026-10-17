import type { BattingSeason, ChartSeason, PitchingSeason } from '../types';

// A position player's mop-up innings don't make him a pitcher; 100 IP of real
// pitching does (Ruth, Ohtani).
const TWO_WAY_MIN_IP_OUTS = 300;

/**
 * Which stat lines a player's views should show. Having batting rows isn't
 * enough: pre-DH and NL pitchers bat, so a primary pitcher is not a batter.
 * Without a primary position, fall back to the leaderboard's rule (more
 * pitching WAR than batting WAR means pitcher).
 */
export function playerRoles(
  primaryPosition: string | null,
  batting: BattingSeason[],
  pitching: PitchingSeason[],
): { isBatter: boolean; isPitcher: boolean } {
  const hasBat = batting.length > 0;
  const hasPit = pitching.length > 0;
  const war = (rows: { war: number | null }[]) => rows.reduce((n, s) => n + (s.war ?? 0), 0);
  const primaryP = primaryPosition
    ? primaryPosition === 'P'
    : hasPit && (!hasBat || war(pitching) > war(batting));
  const outs = pitching.reduce((n, s) => n + (s.ip_outs ?? 0), 0);
  return {
    isBatter: hasBat && !primaryP,
    isPitcher: hasPit && (primaryP || outs >= TWO_WAY_MIN_IP_OUTS),
  };
}

function round1(n: number) {
  return Math.round(n * 10) / 10;
}

function ageAtMidSeason(season: number, birthDate: string): number {
  const birth = new Date(birthDate);
  const midSeason = new Date(Date.UTC(season, 6, 1)); // July 1
  let age = season - birth.getUTCFullYear();
  const birthdayThisYear = new Date(Date.UTC(season, birth.getUTCMonth(), birth.getUTCDate()));
  if (midSeason < birthdayThisYear) age--;
  return age;
}

export function mergeSeasons(batting: BattingSeason[], pitching: PitchingSeason[], birthDate: string | null): ChartSeason[] {
  // _pitchingSO is tracked separately so NL pitchers (who have batting seasons with hr=0)
  // still show pitching strikeouts rather than their negligible batting strikeout totals.
  const map = new Map<number, ChartSeason & { _battingPA: number; _pitchingIP: number; _pitchingSO: number }>();

  for (const s of batting) {
    const existing = map.get(s.year);
    const pa = s.plate_appearances ?? 0;
    if (existing) {
      existing.war = round1((existing.war ?? 0) + (s.war ?? 0));
      existing.hr  = (existing.hr ?? 0) + (s.home_runs ?? 0);
      existing.pa  = (existing.pa ?? 0) + pa;
      existing.ab  = (existing.ab ?? 0) + (s.at_bats ?? 0);
      existing.h   = (existing.h ?? 0) + (s.hits ?? 0);
      if (pa > existing._battingPA) {
        existing.avg      = s.batting_avg;
        existing.ops      = s.ops;
        existing.ops_plus = pa >= 130 ? s.ops_plus : null;
        existing._battingPA = pa;
      }
      existing.so = (existing.so ?? 0) + (s.strikeouts ?? 0);
    } else {
      map.set(s.year, {
        season: s.year,
        age: null,
        war: s.war,
        hr: s.home_runs,
        avg: s.batting_avg,
        ops: s.ops,
        ops_plus: pa >= 130 ? s.ops_plus : null,
        era: null,
        era_plus: null,
        so: s.strikeouts,
        pa,
        ab: s.at_bats ?? 0,
        h: s.hits ?? 0,
        ip_outs: 0,
        er: 0,
        _battingPA: pa,
        _pitchingIP: 0,
        _pitchingSO: 0,
      });
    }
  }

  for (const s of pitching) {
    const existing = map.get(s.year);
    const ip = s.ip_outs ?? 0;
    if (existing) {
      existing.war = round1((existing.war ?? 0) + (s.war ?? 0));
      existing.ip_outs = (existing.ip_outs ?? 0) + ip;
      existing.er      = (existing.er ?? 0) + (s.earned_runs ?? 0);
      if (ip > existing._pitchingIP) {
        existing.era      = s.era;
        existing.era_plus = ip >= 30 ? s.era_plus : null;
        existing._pitchingIP = ip;
      }
      existing._pitchingSO += s.strikeouts ?? 0;
    } else {
      map.set(s.year, {
        season: s.year,
        age: null,
        war: s.war,
        hr: null,
        avg: null,
        ops: null,
        ops_plus: null,
        era: s.era,
        era_plus: ip >= 30 ? s.era_plus : null,
        so: s.strikeouts,
        pa: 0,
        ab: 0,
        h: 0,
        ip_outs: ip,
        er: s.earned_runs ?? 0,
        _battingPA: 0,
        _pitchingIP: ip,
        _pitchingSO: s.strikeouts ?? 0,
      });
    }
  }

  return [...map.values()]
    .sort((a, b) => a.season - b.season)
    .map(({ _battingPA: _b, _pitchingIP: _p, _pitchingSO: ps, ...rest }) => ({
      ...rest,
      // Prefer pitching SO when present — NL pitchers have hr=0 not null,
      // so the old hr===null guard would silently drop 300-K seasons.
      so: ps > 0 ? ps : rest.so,
      age: birthDate != null ? ageAtMidSeason(rest.season, birthDate) : null,
    }));
}
