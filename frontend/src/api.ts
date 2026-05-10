import type {
  PaginatedResponse,
  PlayerSummary,
  PlayerDetail,
  BattingSeason,
  PitchingSeason,
  SimilarPlayersResponse,
  PlayerAward,
  ZoneRole,
  ZoneOutcome,
  ZoneResponse,
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

export function fetchSimilarPlayers(bbrefId: string): Promise<SimilarPlayersResponse> {
  return get<SimilarPlayersResponse>(`/players/${bbrefId}/similar/`);
}

export function fetchPlayerAwards(bbrefId: string): Promise<PlayerAward[]> {
  return get<PlayerAward[]>(`/players/${bbrefId}/awards/`);
}

export function fetchPitchZone(
  bbrefId: string,
  role: ZoneRole,
  outcome: ZoneOutcome,
): Promise<ZoneResponse> {
  const params = new URLSearchParams({ role, outcome });
  return get<ZoneResponse>(`/players/${bbrefId}/pitch_zone/?${params}`);
}
