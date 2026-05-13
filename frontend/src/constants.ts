import type { Metric } from './types';

export const METRICS: Metric[] = [
  { id: 'war',      label: 'WAR',  full: 'Wins Above Replacement' },
  { id: 'hr',       label: 'HR',   full: 'Home Runs' },
  { id: 'avg',      label: 'AVG',  full: 'Batting Average' },
  { id: 'ops',      label: 'OPS',  full: 'On-base + Slugging' },
  { id: 'ops_plus', label: 'OPS+', full: 'Era-adjusted OPS (100 = avg)' },
  { id: 'era',      label: 'ERA',  full: 'Earned Run Average' },
  { id: 'era_plus', label: 'ERA+', full: 'Era-adjusted ERA (100 = avg, higher = better)' },
  { id: 'so',       label: 'SO',   full: 'Strikeouts' },
];

/** 10 vibrant, perceptually distinct colors at consistent oklch chroma — matches design palette. */
export const PLAYER_COLORS = [
  '#22d3ee', // cyan
  '#f59e0b', // amber
  '#e879f9', // magenta
  '#a3e635', // lime
  '#a78bfa', // violet
  '#fb923c', // orange
  '#2dd4bf', // teal
  '#fb7185', // rose
  '#60a5fa', // sky
  '#facc15', // yellow
] as const;

export const MAX_PLAYERS = 10;
