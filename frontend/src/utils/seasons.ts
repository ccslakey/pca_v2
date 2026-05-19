import type { BattingSeason, ChartSeason, PitchingSeason } from '../types';

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

/** Merge batting + pitching season arrays into ChartSeason[] (one entry per year). */
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
      // keep rate stats from the stint with more plate appearances
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
      // ERA / ERA+: keep from the stint with most ip_outs
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
