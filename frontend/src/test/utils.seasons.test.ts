import { describe, it, expect } from 'vitest';
import { mergeSeasons } from '../utils/seasons';
import type { BattingSeason, PitchingSeason } from '../types';

function bat(year: number, overrides: Partial<BattingSeason> = {}): BattingSeason {
  return {
    id: year, player: 'testpl01', year, stint: 1, team: 'NYA', league: 'AL',
    games: 150, plate_appearances: 600, at_bats: 530, runs: 80, hits: 150,
    doubles: 30, triples: 2, home_runs: 20, rbi: 80, stolen_bases: 5,
    caught_stealing: 2, walks: 60, strikeouts: 120, ibb: 3, hbp: 4,
    sacrifice_hits: 1, sacrifice_flies: 5, gidp: 10, total_bases: 260,
    batting_avg: 0.280, on_base_pct: 0.360, slugging_pct: 0.490,
    ops: 0.850, ops_plus: 130, war: 4.0,
    ...overrides,
  };
}

function pit(year: number, overrides: Partial<PitchingSeason> = {}): PitchingSeason {
  return {
    id: year + 1000, player: 'testpl01', year, stint: 1, team: 'NYA', league: 'AL',
    wins: 15, losses: 8, games: 32, games_started: 32, complete_games: 2,
    sho: 1, saves: 0, games_finished: 0, ip_outs: 630, hits_allowed: 180,
    runs_allowed: 80, earned_runs: 75, home_runs: 20, walks: 60, ibb: 5,
    strikeouts: 200, hbp: 8, wild_pitches: 4, balks: 0, bfp: 850,
    sacrifice_flies: 6, gidp: 15, era: 3.20, era_plus: 125, fip: 3.10,
    whip: 1.18, hits_per_nine: 7.8, home_runs_per_nine: 0.9,
    walks_per_nine: 2.6, strikeouts_per_nine: 8.6, strikeouts_per_walk: 3.3,
    war: 5.0,
    ...overrides,
  };
}

describe('mergeSeasons', () => {
  it('returns empty array for no input', () => {
    expect(mergeSeasons([], [], null)).toEqual([]);
  });

  it('maps a single batting season', () => {
    const result = mergeSeasons([bat(2010)], [], null);
    expect(result).toHaveLength(1);
    expect(result[0].season).toBe(2010);
    expect(result[0].war).toBe(4.0);
    expect(result[0].hr).toBe(20);
    expect(result[0].avg).toBe(0.280);
  });

  it('maps a single pitching season', () => {
    const result = mergeSeasons([], [pit(2010)], null);
    expect(result).toHaveLength(1);
    expect(result[0].season).toBe(2010);
    expect(result[0].war).toBe(5.0);
    expect(result[0].era).toBe(3.20);
    expect(result[0].hr).toBeNull();
  });

  it('sorts seasons by year', () => {
    const result = mergeSeasons([bat(2012), bat(2010), bat(2011)], [], null);
    expect(result.map(s => s.season)).toEqual([2010, 2011, 2012]);
  });

  it('sums WAR across batting + pitching in same year (two-way)', () => {
    const result = mergeSeasons([bat(2015, { war: 3.0 })], [pit(2015, { war: 2.0 })], null);
    expect(result).toHaveLength(1);
    expect(result[0].war).toBe(5.0);
  });

  it('keeps batting hr and pitching era in the same merged season', () => {
    const result = mergeSeasons([bat(2015, { home_runs: 10 })], [pit(2015, { era: 2.50 })], null);
    expect(result[0].hr).toBe(10);
    expect(result[0].era).toBe(2.50);
  });

  it('sums WAR across multi-team batting stints', () => {
    const s1 = bat(2010, { stint: 1, war: 2.0, plate_appearances: 300 });
    const s2 = bat(2010, { stint: 2, war: 1.5, plate_appearances: 200, team: 'BOS' });
    const result = mergeSeasons([s1, s2], [], null);
    expect(result).toHaveLength(1);
    expect(result[0].war).toBe(3.5);
  });

  it('keeps rate stats from the higher-PA batting stint', () => {
    const bigStint  = bat(2010, { stint: 1, plate_appearances: 400, batting_avg: 0.300, ops: 0.900, ops_plus: 140 });
    const smallStint = bat(2010, { stint: 2, plate_appearances: 100, batting_avg: 0.220, ops: 0.650, ops_plus: 90, team: 'BOS' });
    const result = mergeSeasons([bigStint, smallStint], [], null);
    expect(result[0].avg).toBe(0.300);
    expect(result[0].ops).toBe(0.900);
    expect(result[0].ops_plus).toBe(140);
  });

  it('nulls ops_plus when PA < 130', () => {
    const result = mergeSeasons([bat(2010, { plate_appearances: 100, ops_plus: 150 })], [], null);
    expect(result[0].ops_plus).toBeNull();
  });

  it('retains ops_plus when PA >= 130', () => {
    const result = mergeSeasons([bat(2010, { plate_appearances: 130, ops_plus: 150 })], [], null);
    expect(result[0].ops_plus).toBe(150);
  });

  it('nulls era_plus when ip_outs < 30', () => {
    const result = mergeSeasons([], [pit(2010, { ip_outs: 20, era_plus: 140 })], null);
    expect(result[0].era_plus).toBeNull();
  });

  it('uses pitching SO over batting SO for NL pitchers (hr=0 not null)', () => {
    // NL pitcher has a batting season (hr=0, small SO) and a dominant pitching season
    const batting = bat(2005, { home_runs: 0, strikeouts: 30, plate_appearances: 200 });
    const pitching = pit(2005, { strikeouts: 250 });
    const result = mergeSeasons([batting], [pitching], null);
    expect(result[0].so).toBe(250);
  });

  it('falls back to batting SO when no pitching SO', () => {
    const result = mergeSeasons([bat(2010, { strikeouts: 100 })], [], null);
    expect(result[0].so).toBe(100);
  });

  it('computes age from birthDate at mid-season (July 1)', () => {
    // Born June 1, 1980 — already had birthday by July 1 → age = season - birth year
    const result = mergeSeasons([bat(2010)], [], '1980-06-01');
    expect(result[0].age).toBe(30);
  });

  it('decrements age when birthday is after July 1', () => {
    // Born August 1, 1980 — birthday not yet reached by July 1 → age = 29
    const result = mergeSeasons([bat(2010)], [], '1980-08-01');
    expect(result[0].age).toBe(29);
  });

  it('sets age to null when birthDate is null', () => {
    const result = mergeSeasons([bat(2010)], [], null);
    expect(result[0].age).toBeNull();
  });
});
