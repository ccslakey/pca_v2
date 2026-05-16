export interface ArticleMeta {
  slug: string;
  title: string;
  description: string;
  readingTimeMin: number;
}

export const ARTICLES: ArticleMeta[] = [
  {
    slug: 'war',
    title: 'WAR: Source & Scope',
    description: 'Which WAR system is used, why bWAR over fWAR, and how career totals are computed.',
    readingTimeMin: 3,
  },
  {
    slug: 'era-adjusted-metrics',
    title: 'Era-Adjusted Metrics',
    description: 'How OPS+ and ERA+ are calculated, why they enable cross-era comparison, and where our career figures diverge from Baseball Reference.',
    readingTimeMin: 3,
  },
  {
    slug: 'similarity',
    title: 'Similarity Engine',
    description: 'The weighted-Euclidean k-NN behind the similar players panel: feature vectors, z-scoring, calibrated scoring, and known limitations.',
    readingTimeMin: 5,
  },
  {
    slug: 'awards',
    title: 'Award Tracking',
    description: 'The 13 award types on the chart, their year coverage, and how glyph priority resolution works when a player wins multiple things in one season.',
    readingTimeMin: 2,
  },
  {
    slug: 'james-scores',
    title: 'Hall of Fame Metrics',
    description: 'Bill James\'s Black Ink, Gray Ink, and HOF Monitor scores: what they measure, qualification thresholds, and where our numbers may differ from BBref.',
    readingTimeMin: 3,
  },
  {
    slug: 'positions',
    title: 'Primary Position Assignment',
    description: 'How primary position is derived from Baseball Reference fielding data and where multi-position players and late-career DHs may be misclassified.',
    readingTimeMin: 2,
  },
  {
    slug: 'leaderboard',
    title: 'Leaderboard & Qualification',
    description: 'The career WAR floor for leaderboard inclusion, how career and peak WAR are computed, and how the era and position filters work.',
    readingTimeMin: 2,
  },
  {
    slug: 'pitch-zones',
    title: 'Pitch Zone Heatmaps',
    description: 'Statcast zone data: 2015+ coverage, how pitch coordinates are bucketed, what contact/hit/whiff rates mean, and sample-size caveats.',
    readingTimeMin: 2,
  },
  {
    slug: 'data',
    title: 'Data Sources & Freshness',
    description: 'Where the data comes from, update frequency during and after the season, known lag, and what\'s explicitly out of scope.',
    readingTimeMin: 2,
  },
  {
    slug: 'divergences',
    title: 'Divergences from Baseball Reference',
    description: 'Every known case where our numbers differ from BBref and why — WAR rounding, OPS+ weighting method, James score tie-breaking, and more.',
    readingTimeMin: 3,
  },
];

export function getArticle(slug: string): ArticleMeta | undefined {
  return ARTICLES.find(a => a.slug === slug);
}
