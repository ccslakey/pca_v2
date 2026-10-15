import type { Metric, MetricId } from './types';

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

/**
 * Natural-language lookups for metrics that the methodology corpus actually
 * documents. Only these metrics get an inline explainer; others have no
 * dedicated doc, so we don't surface a weak retrieval result.
 */
export const METRIC_QUERIES: Partial<Record<MetricId, string>> = {
  war: 'which WAR system is used, why bWAR over fWAR, and how career WAR is computed',
  ops_plus: 'what does OPS+ mean and how is it calculated',
  era_plus: 'what does ERA+ mean and how is it calculated',
};

export const PLAYER_COLORS = [
  '#22d3ee',
  '#f59e0b',
  '#e879f9',
  '#a3e635',
  '#a78bfa',
  '#fb923c',
  '#2dd4bf',
  '#fb7185',
  '#60a5fa',
  '#facc15',
] as const;

export const MAX_PLAYERS = 10;
