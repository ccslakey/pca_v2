import { useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchAgingCurve, fetchFeatured, fetchLeaderboard, fetchMethodologySearch, fetchNarrative, fetchPlayer, fetchPlayerAwards, fetchPlayerBundle, fetchPitchZone, fetchSimilarPlayers, searchPlayers } from './api';
import type { ZoneOutcome, ZoneRole, LeaderboardFilters } from './types';
import type { ChartPlayer } from './types';
import { initials, posLabel } from './utils/format';
import { mergeSeasons } from './utils/seasons';

export function useFeatured() {
  return useQuery({
    queryKey: ['featured'],
    queryFn: fetchFeatured,
    staleTime: Infinity, // server caches; this list never changes between deploys
  });
}

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

export function usePlayerBundle(bbrefId: string | null) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ['playerBundle', bbrefId],
    queryFn: async () => {
      const data = await fetchPlayerBundle(bbrefId!);
      // Populate per-key caches so existing consumers (usePlayerDetail,
      // usePlayerAwards, etc.) get cache hits instead of firing new requests.
      queryClient.setQueryData(['player',   bbrefId], data.detail);
      queryClient.setQueryData(['batting',  bbrefId], data.batting);
      queryClient.setQueryData(['pitching', bbrefId], data.pitching);
      queryClient.setQueryData(['awards',   bbrefId], data.awards);
      return data;
    },
    enabled: bbrefId != null,
    staleTime: Infinity,
  });
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

export function useAgingCurve(role: 'B' | 'P' | null) {
  return useQuery({
    queryKey: ['agingCurve', role],
    queryFn: () => fetchAgingCurve(role!),
    enabled: role != null,
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

export function useNarrative(bbrefId: string | null) {
  return useQuery({
    queryKey: ['narrative', bbrefId],
    queryFn: () => fetchNarrative(bbrefId!),
    enabled: bbrefId != null,
    staleTime: Infinity, // server caches per data version
  });
}

export function useMethodologySearch(query: string | null) {
  return useQuery({
    queryKey: ['methodology', query],
    queryFn: () => fetchMethodologySearch(query!),
    enabled: query != null && query.length > 0,
    staleTime: Infinity, // corpus is static between re-indexes
  });
}

/** Load all data for one selected player and build a ChartPlayer. */
export function useChartPlayer(bbrefId: string | null, colorIndex: number): {
  data: ChartPlayer | undefined;
  isLoading: boolean;
} {
  const { data: bundle, isLoading } = usePlayerBundle(bbrefId);

  if (!bundle) {
    return { data: undefined, isLoading };
  }

  const { detail: p, batting: bat, pitching: pit, awards } = bundle;
  const hasBat = bat.length > 0;
  const hasPit = pit.length > 0;

  const debutYear = p.debut      ? new Date(p.debut).getUTCFullYear()      : null;
  const finalYear = p.final_game ? new Date(p.final_game).getUTCFullYear() : null;
  const years = debutYear && finalYear ? `${debutYear}–${finalYear}` : 'Active';

  const pos = posLabel(p.primary_position, p.throws, hasPit);
  const wp  = p.war_percentile;

  const chartPlayer: ChartPlayer = {
    id: p.bbref_id,
    name: `${p.first_name} ${p.last_name}`,
    color: `var(--chart-${(colorIndex % 10) + 1})`,
    initials: initials(`${p.first_name} ${p.last_name}`),
    pos,
    years,
    seasons: mergeSeasons(bat, pit, p.birth_date),
    isBatter: hasBat,
    isPitcher: hasPit,
    awards,
    birthYear: p.birth_date ? new Date(p.birth_date).getUTCFullYear() : null,
    warPercentile: wp ? { topPct: wp.top_pct, position: wp.position, rank: wp.rank, n: wp.n } : null,
  };

  return { data: chartPlayer, isLoading: false };
}

export interface PlayerSlot {
  id: string;
  player: ChartPlayer | undefined;
  isLoading: boolean;
}

/**
 * Load up to 10 selected players into ChartPlayer slots. Hooks must be called
 * unconditionally, so all ten useChartPlayer calls fire every render and unused
 * slots resolve to undefined. Shared by desktop ComparePage and mobile Compare.
 */
export function useChartPlayers(selectedIds: string[]): PlayerSlot[] {
  const p0 = useChartPlayer(selectedIds[0] ?? null, 0);
  const p1 = useChartPlayer(selectedIds[1] ?? null, 1);
  const p2 = useChartPlayer(selectedIds[2] ?? null, 2);
  const p3 = useChartPlayer(selectedIds[3] ?? null, 3);
  const p4 = useChartPlayer(selectedIds[4] ?? null, 4);
  const p5 = useChartPlayer(selectedIds[5] ?? null, 5);
  const p6 = useChartPlayer(selectedIds[6] ?? null, 6);
  const p7 = useChartPlayer(selectedIds[7] ?? null, 7);
  const p8 = useChartPlayer(selectedIds[8] ?? null, 8);
  const p9 = useChartPlayer(selectedIds[9] ?? null, 9);

  const all = [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9];

  return useMemo(() => selectedIds.map((id, i) => ({
    id,
    player: all[i]?.data,
    isLoading: all[i]?.isLoading ?? false,
  })),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [selectedIds.join(','), p0.data, p1.data, p2.data, p3.data, p4.data, p5.data, p6.data, p7.data, p8.data, p9.data, p0.isLoading, p1.isLoading, p2.isLoading, p3.isLoading, p4.isLoading, p5.isLoading, p6.isLoading, p7.isLoading, p8.isLoading, p9.isLoading]);
}
