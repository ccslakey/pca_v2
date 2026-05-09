import { useQuery } from '@tanstack/react-query';
import { fetchBattingSeasons, fetchPitchingSeasons, fetchPlayer, fetchSimilarPlayers, searchPlayers } from './api';
import type { BattingSeason, ChartPlayer, ChartSeason, PitchingSeason } from './types';
import { PLAYER_COLORS } from './constants';

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

/** Merge batting + pitching season arrays into ChartSeason[] (one entry per year). */
function mergeSeasons(batting: BattingSeason[], pitching: PitchingSeason[]): ChartSeason[] {
  const map = new Map<number, ChartSeason & { _battingPA: number; _pitchingIP: number }>();

  for (const s of batting) {
    const existing = map.get(s.year);
    if (existing) {
      existing.war = round1((existing.war ?? 0) + (s.war ?? 0));
      existing.hr  = (existing.hr ?? 0) + (s.home_runs ?? 0);
      // keep rate stats from the stint with more plate appearances
      if ((s.plate_appearances ?? 0) > existing._battingPA) {
        existing.avg = s.batting_avg;
        existing.ops = s.ops;
        existing._battingPA = s.plate_appearances ?? 0;
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
        era: null,
        so: s.strikeouts,
        _battingPA: s.plate_appearances ?? 0,
        _pitchingIP: 0,
      });
    }
  }

  for (const s of pitching) {
    const existing = map.get(s.year);
    if (existing) {
      existing.war = round1((existing.war ?? 0) + (s.war ?? 0));
      // ERA: keep from the stint with most ip_outs
      if ((s.ip_outs ?? 0) > existing._pitchingIP) {
        existing.era = s.era;
        existing._pitchingIP = s.ip_outs ?? 0;
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
        era: s.era,
        so: s.strikeouts,
        _battingPA: 0,
        _pitchingIP: s.ip_outs ?? 0,
      });
    }
  }

  return [...map.values()]
    .sort((a, b) => a.season - b.season)
    .map(({ _battingPA: _b, _pitchingIP: _p, ...rest }) => rest);
}

function round1(n: number) {
  return Math.round(n * 10) / 10;
}

function initials(firstName: string, lastName: string) {
  return `${firstName[0] ?? ''}${lastName[0] ?? ''}`.toUpperCase();
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

  const isLoading = detail.isLoading || batting.isLoading || pitching.isLoading;

  if (!detail.data || !batting.data || !pitching.data) {
    return { data: undefined, isLoading };
  }

  const p      = detail.data;
  const bat    = batting.data;
  const pit    = pitching.data;
  const hasBat = bat.length > 0;
  const hasPit = pit.length > 0;

  const years =
    p.mlb_played_first && p.mlb_played_last
      ? `${p.mlb_played_first}–${p.mlb_played_last}`
      : 'Active';

  const pos = hasBat && hasPit ? 'B/P' : hasPit ? 'P' : 'B';

  const chartPlayer: ChartPlayer = {
    id: p.bbref_id,
    name: `${p.first_name} ${p.last_name}`,
    color: PLAYER_COLORS[colorIndex % PLAYER_COLORS.length],
    initials: initials(p.first_name, p.last_name),
    pos,
    years,
    seasons: mergeSeasons(bat, pit),
    isBatter: hasBat,
    isPitcher: hasPit,
  };

  return { data: chartPlayer, isLoading: false };
}
