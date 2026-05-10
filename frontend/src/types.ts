// ---- API response shapes (match Django serializers) ----

export interface PlayerSummary {
  bbref_id: string;
  first_name: string;
  last_name: string;
  mlb_played_first: number | null;
  mlb_played_last: number | null;
  bats: string | null;
  throws: string | null;
}

export interface PlayerDetail extends PlayerSummary {
  mlbam_id: number | null;
  fangraphs_id: number | null;
  retro_id: string | null;
  birth_year: number | null;
  birth_country: string | null;
  debut: string | null;
  final_game: string | null;
}

export interface BattingSeason {
  id: number;
  player: string;
  year: number;
  stint: number;
  team: string;
  league: string | null;
  games: number | null;
  plate_appearances: number | null;
  at_bats: number | null;
  runs: number | null;
  hits: number | null;
  doubles: number | null;
  triples: number | null;
  home_runs: number | null;
  rbi: number | null;
  stolen_bases: number | null;
  caught_stealing: number | null;
  walks: number | null;
  strikeouts: number | null;
  ibb: number | null;
  hbp: number | null;
  sacrifice_hits: number | null;
  sacrifice_flies: number | null;
  gidp: number | null;
  total_bases: number | null;
  batting_avg: number | null;
  on_base_pct: number | null;
  slugging_pct: number | null;
  ops: number | null;
  ops_plus: number | null;
  war: number | null;
}

export interface PitchingSeason {
  id: number;
  player: string;
  year: number;
  stint: number;
  team: string;
  league: string | null;
  wins: number | null;
  losses: number | null;
  games: number | null;
  games_started: number | null;
  complete_games: number | null;
  sho: number | null;
  saves: number | null;
  games_finished: number | null;
  ip_outs: number | null;
  hits_allowed: number | null;
  runs_allowed: number | null;
  earned_runs: number | null;
  home_runs: number | null;
  walks: number | null;
  ibb: number | null;
  strikeouts: number | null;
  hbp: number | null;
  wild_pitches: number | null;
  balks: number | null;
  bfp: number | null;
  sacrifice_flies: number | null;
  gidp: number | null;
  era: number | null;
  era_plus: number | null;
  fip: number | null;
  whip: number | null;
  hits_per_nine: number | null;
  home_runs_per_nine: number | null;
  walks_per_nine: number | null;
  strikeouts_per_nine: number | null;
  strikeouts_per_walk: number | null;
  war: number | null;
}

export type AwardKind =
  | 'mvp' | 'cy' | 'roty' | 'gg' | 'ss'
  | 'tc_b' | 'tc_p' | 'hof' | 'postmvp'
  | 'bat_title' | 'era_title' | 'all_mlb' | 'ws' | 'asg';

export interface PlayerAward {
  id: number;
  year: number;
  kind: AwardKind;
  league: string | null;
  notes: string | null;
}

export interface SimilarPlayer {
  bbref_id: string;
  first_name: string;
  last_name: string;
  mlb_played_first: number | null;
  mlb_played_last: number | null;
  career_war: number;
  is_pitcher: boolean;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ---- Chart domain types ----

export type MetricId = 'war' | 'hr' | 'avg' | 'ops' | 'era' | 'so';

export interface Metric {
  id: MetricId;
  label: string;
  full: string;
}

/** One x-axis data point per player per season on the chart. */
export interface ChartSeason {
  season: number;
  age: number | null;
  war: number | null;
  hr: number | null;
  avg: number | null;
  ops: number | null;
  era: number | null;
  so: number | null;
}

/** A player's full data as needed by the chart and cards. */
export interface ChartPlayer {
  id: string;           // bbref_id
  name: string;
  color: string;
  initials: string;
  pos: string;          // primary position label (B / P / B+P)
  years: string;
  seasons: ChartSeason[];
  isPitcher: boolean;
  isBatter: boolean;
}
