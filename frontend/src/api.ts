import type {
  PaginatedResponse,
  PlayerSummary,
  PlayerDetail,
  BattingSeason,
  PitchingSeason,
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
