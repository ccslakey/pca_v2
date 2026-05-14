import type {
  PaginatedResponse,
  PlayerSummary,
  PlayerDetail,
  BattingSeason,
  FeaturedResponse,
  FieldingSeason,
  PitchingSeason,
  SimilarPlayersResponse,
  PlayerAward,
  ZoneRole,
  ZoneOutcome,
  ZoneResponse,
  LeaderboardResponse,
  LeaderboardFilters,
} from './types';

const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export function searchPlayers(q: string): Promise<PaginatedResponse<PlayerSummary>> {
  const params = new URLSearchParams({ search: q, page_size: '15' });
  return get<PaginatedResponse<PlayerSummary>>(`/players/?${params}`);
}

export function fetchPlayer(bbrefId: string): Promise<PlayerDetail> {
  return get<PlayerDetail>(`/players/${bbrefId}/`);
}

export function fetchBattingSeasons(bbrefId: string): Promise<BattingSeason[]> {
  return get<BattingSeason[]>(`/players/${bbrefId}/batting/`);
}

export function fetchPitchingSeasons(bbrefId: string): Promise<PitchingSeason[]> {
  return get<PitchingSeason[]>(`/players/${bbrefId}/pitching/`);
}

export function fetchFieldingSeasons(bbrefId: string): Promise<FieldingSeason[]> {
  return get<FieldingSeason[]>(`/players/${bbrefId}/fielding/`);
}

export function fetchSimilarPlayers(bbrefId: string): Promise<SimilarPlayersResponse> {
  return get<SimilarPlayersResponse>(`/players/${bbrefId}/similar/`);
}

export function fetchPlayerAwards(bbrefId: string): Promise<PlayerAward[]> {
  return get<PlayerAward[]>(`/players/${bbrefId}/awards/`);
}

export function fetchLeaderboard(filters: LeaderboardFilters = {}): Promise<LeaderboardResponse> {
  const params = new URLSearchParams();
  if (filters.pos)       params.set('pos', filters.pos);
  if (filters.min_war)   params.set('min_war', String(filters.min_war));
  if (filters.era_start) params.set('era_start', String(filters.era_start));
  if (filters.era_end)   params.set('era_end', String(filters.era_end));
  if (filters.sort)      params.set('sort', filters.sort);
  if (filters.order)     params.set('order', filters.order);
  if (filters.page)      params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  return get<LeaderboardResponse>(`/players/leaderboard/?${params}`);
}

export function fetchMeta(): Promise<{ last_updated: string | null }> {
  return get<{ last_updated: string | null }>('/meta/');
}

export function fetchFeatured(): Promise<FeaturedResponse> {
  return get<FeaturedResponse>('/players/featured/');
}

export function fetchPitchZone(
  bbrefId: string,
  role: ZoneRole,
  outcome: ZoneOutcome,
): Promise<ZoneResponse> {
  const params = new URLSearchParams({ role, outcome });
  return get<ZoneResponse>(`/players/${bbrefId}/pitch_zone/?${params}`);
}
