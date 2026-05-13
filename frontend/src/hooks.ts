import { useQuery } from '@tanstack/react-query';
import { fetchBattingSeasons, fetchLeaderboard, fetchPitchingSeasons, fetchPlayer, fetchPlayerAwards, fetchPitchZone, fetchSimilarPlayers, searchPlayers } from './api';
import type { ZoneOutcome, ZoneRole, LeaderboardFilters } from './types';
import type { BattingSeason, ChartPlayer, ChartSeason, PitchingSeason } from './types';
import { PLAYER_COLORS } from './constants';
import { posLabel } from './utils/format';

export function useLeaderboard(filters: LeaderboardFilters) {
  return useQuery({
    queryKey: ['leaderboard', filters],
    queryFn: () => fetchLeaderboard(filters),
    staleTime: 1000 * 60 * 5,
    placeholderData: (prev) => prev,
  });
}

export function usePlayerSearch(q: string) {
  return useQuery({
    queryKey: ['playerSearch', q],
    queryFn: () => searchPlayers(q),
    enabled: q.length >= 1,
    staleTime: 60_000,
  });
}

export function usePlayerDetail(bbrefId: string | null) {
  return useQuery({
    queryKey: ['player', bbrefId],
    queryFn: () => fetchPlayer(bbrefId!),
    enabled: bbrefId != null,
    staleTime: Infinity,
  });
}

function useBattingSeasons(bbrefId: string | null) {
  return useQuery({
    queryKey: ['batting', bbrefId],
    queryFn: () => fetchBattingSeasons(bbrefId!),
    enabled: bbrefId != null,
    staleTime: Infinity,
  });
}

function usePitchingSeasons(bbrefId: string | null) {
  return useQuery({
    queryKey: ['pitching', bbrefId],
    queryFn: () => fetchPitchingSeasons(bbrefId!),
    enabled: bbrefId != null,
    staleTime: Infinity,
  });
}

function ageAtMidSeason(season: number, birthDate: string): number {
  const birth  = new Date(birthDate);
  const midSeason = new Date(Date.UTC(season, 6, 1)); // July 1
  let age = season - birth.getUTCFullYear();
  const birthdayThisYear = new Date(Date.UTC(season, birth.getUTCMonth(), birth.getUTCDate()));
  if (midSeason < birthdayThisYear) age--;
  return age;
}

/** Merge batting + pitching season arrays into ChartSeason[] (one entry per year). */
function mergeSeasons(batting: BattingSeason[], pitching: PitchingSeason[], birthDate: string | null): ChartSeason[] {
  const map = new Map<number, ChartSeason & { _battingPA: number; _pitchingIP: number }>();

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
      // pitching strikeouts add on top (two-way player)
      if (existing.hr === null) existing.so = (existing.so ?? 0) + (s.strikeouts ?? 0);
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
      });
    }
  }

  return [...map.values()]
    .sort((a, b) => a.season - b.season)
    .map(({ _battingPA: _b, _pitchingIP: _p, ...rest }) => ({
      ...rest,
      age: birthDate != null ? ageAtMidSeason(rest.season, birthDate) : null,
    }));
}

function round1(n: number) {
  return Math.round(n * 10) / 10;
}

function initials(firstName: string, lastName: string) {
  return `${firstName[0] ?? ''}${lastName[0] ?? ''}`.toUpperCase();
}

export function usePitchZone(
  bbrefId: string | null,
  role: ZoneRole,
  outcome: ZoneOutcome,
) {
  return useQuery({
    queryKey: ['pitchZone', bbrefId, role, outcome],
    queryFn: () => fetchPitchZone(bbrefId!, role, outcome),
    enabled: bbrefId != null,
    staleTime: Infinity,
  });
}

export function usePlayerAwards(bbrefId: string | null) {
  return useQuery({
    queryKey: ['awards', bbrefId],
    queryFn: () => fetchPlayerAwards(bbrefId!),
    enabled: bbrefId != null,
    staleTime: Infinity,
  });
}

export function useSimilarPlayers(bbrefId: string | null) {
  return useQuery({
    queryKey: ['similar', bbrefId],
    queryFn: () => fetchSimilarPlayers(bbrefId!),
    enabled: bbrefId != null,
    staleTime: Infinity,
  });
}

/** Load all data for one selected player and build a ChartPlayer. */
export function useChartPlayer(bbrefId: string | null, colorIndex: number): {
  data: ChartPlayer | undefined;
  isLoading: boolean;
} {
  const detail   = usePlayerDetail(bbrefId);
  const batting  = useBattingSeasons(bbrefId);
  const pitching = usePitchingSeasons(bbrefId);
  const awards   = usePlayerAwards(bbrefId);

  const isLoading = detail.isLoading || batting.isLoading || pitching.isLoading || awards.isLoading;

  if (!detail.data || !batting.data || !pitching.data || !awards.data) {
    return { data: undefined, isLoading };
  }

  const p      = detail.data;
  const bat    = batting.data;
  const pit    = pitching.data;
  const hasBat = bat.length > 0;
  const hasPit = pit.length > 0;

  const debutYear     = p.debut     ? new Date(p.debut).getUTCFullYear()     : null;
  const finalYear     = p.final_game ? new Date(p.final_game).getUTCFullYear() : null;
  const years = debutYear && finalYear ? `${debutYear}–${finalYear}` : 'Active';

  const pos = posLabel(p.primary_position, p.throws, hasPit);

  const chartPlayer: ChartPlayer = {
    id: p.bbref_id,
    name: `${p.first_name} ${p.last_name}`,
    color: PLAYER_COLORS[colorIndex % PLAYER_COLORS.length],
    initials: initials(p.first_name, p.last_name),
    pos,
    years,
    seasons: mergeSeasons(bat, pit, p.birth_date),
    isBatter: hasBat,
    isPitcher: hasPit,
    awards: awards.data,
    birthYear: p.birth_date ? new Date(p.birth_date).getUTCFullYear() : null,
  };

  return { data: chartPlayer, isLoading: false };
}
