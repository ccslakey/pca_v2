// ---- API response shapes (match Django serializers) ----

export interface PlayerSummary {
  bbref_id: string;
  first_name: string;
  last_name: string;
  debut: string | null;
  final_game: string | null;
  bats: string | null;
  throws: string | null;
  primary_position: string | null;
}

export interface JamesScore {
  black_ink_bat: number;
  gray_ink_bat: number;
  hof_monitor_bat: number;
  black_ink_pit: number;
  gray_ink_pit: number;
  hof_monitor_pit: number;
}

export interface WarPercentile {
  top_pct: number;
  position: string;
  rank: number;
  n: number;
}

export interface PlayerDetail extends PlayerSummary {
  mlbam_id: number | null;
  fangraphs_id: number | null;
  retro_id: string | null;
  birth_date: string | null;
  birth_country: string | null;
  james_score: JamesScore | null;
  war_percentile: WarPercentile | null;
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

export interface FieldingPositionToken {
  rank: number;
  position: string;
  is_primary_marker: boolean;
  is_minor_marker: boolean;
  is_career_major_marker: boolean;
  is_career_minor_marker: boolean;
  reported_games: number | null;
}

export interface FieldingSeason {
  id: number;
  player: string;
  year: number;
  stint: number;
  team: string;
  league: string | null;
  age: number | null;
  games: number | null;
  games_started: number | null;
  complete_games: number | null;
  innings_outs: number | null;
  chances: number | null;
  putouts: number | null;
  assists: number | null;
  errors: number | null;
  double_plays: number | null;
  fielding_pct: number | null;
  rtot: number | null;
  rtot_per_year: number | null;
  rdrs: number | null;
  rdrs_per_year: number | null;
  range_factor_per_nine: number | null;
  league_range_factor_per_nine: number | null;
  range_factor_per_game: number | null;
  league_range_factor_per_game: number | null;
  passed_balls: number | null;
  wild_pitches: number | null;
  stolen_bases: number | null;
  caught_stealing: number | null;
  caught_stealing_pct: number | null;
  pickoffs: number | null;
  positions_raw: string | null;
  position_tokens: FieldingPositionToken[];
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
  debut: string | null;
  final_game: string | null;
  career_war: number;
  primary_position: string | null;
  throws: string | null;
  is_pitcher: boolean;
  similarity: number;
}

export interface SimilarPlayersResponse {
  batters:  SimilarPlayer[];
  pitchers: SimilarPlayer[];
}

export interface FeaturedTrioPlayer {
  bbref_id: string;
  first_name: string;
  last_name: string;
}

export interface FeaturedTrio {
  slug: string;
  label: string;
  players: FeaturedTrioPlayer[];
}

export interface FeaturedResponse {
  trios: FeaturedTrio[];
}

export type ZoneRole    = 'B' | 'P';
export type ZoneOutcome = 'contact' | 'hits' | 'whiffs';

export interface ZoneBucket {
  plate_x: number;
  plate_z: number;
  count:   number;
  total:   number;
}

export interface ZoneResponse {
  role:    ZoneRole;
  outcome: ZoneOutcome;
  buckets: ZoneBucket[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ---- Leaderboard ----

export interface LeaderboardPlayer {
  bbref_id: string;
  first_name: string;
  last_name: string;
  debut: string | null;
  final_game: string | null;
  primary_position: string | null;
  throws: string | null;
  career_war: number;
  peak_war: number;
  is_pitcher: boolean;
  career_hr: number | null;
  career_era: number | null;
  mvp_count: number;
  cy_count: number;
  gg_count: number;
  asg_count: number;
}

export interface LeaderboardResponse {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: LeaderboardPlayer[];
}

export interface LeaderboardFilters {
  pos?: string;
  min_war?: number;
  era_start?: number;
  era_end?: number;
  sort?: string;
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

// ---- Chart domain types ----

export type MetricId = 'war' | 'hr' | 'avg' | 'ops' | 'ops_plus' | 'era' | 'era_plus' | 'so';

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
  ops_plus: number | null;
  era: number | null;
  era_plus: number | null;
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
  awards: PlayerAward[];
  birthYear: number | null;
  warPercentile: { topPct: number; position: string; rank: number; n: number } | null;
}

export type XMode = 'year' | 'age';
