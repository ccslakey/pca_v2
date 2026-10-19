// Design-sync library entry: the subset of the app's components that render
// from props alone (no live /api calls), plus the providers they need.
// Built by .design-sync/build-ds.mjs into ds-dist/ for the Claude Design sync.
// App code is untouched - this file only re-exports it.
import './fonts.css';
import '../src/globals.scss';

import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../src/themes/ThemeContext';

export { ThemeProvider, useTheme } from '../src/themes/ThemeContext';
export { THEMES } from '../src/themes/themes';
export { METRICS, PLAYER_COLORS, MAX_PLAYERS } from '../src/constants';
// Pure helpers the app uses to derive component props from a ChartPlayer.
export { peakSeason, careerWar, sumMetric, fmtMetric } from '../src/utils/chart';
export { playerColor, colorTint } from '../src/utils/color';

export { Skeleton } from '../src/components/Skeleton';
export { AnnotationGlyph } from '../src/components/AnnotationGlyph';
export { ThemePicker } from '../src/components/layout/ThemePicker';

export { MetricToggle } from '../src/components/compare/MetricToggle';
export { ChipBar } from '../src/components/compare/ChipBar';
export { PlayerCard } from '../src/components/compare/PlayerCard';
export { PlayerCardSkeleton } from '../src/components/compare/PlayerCardSkeleton';
export { ChartSkeleton } from '../src/components/compare/ChartSkeleton';
export { CareerChart } from '../src/components/compare/CareerChart';
export { BrushChart } from '../src/components/compare/BrushChart';

export { ProfileChart } from '../src/components/profile/charts/ProfileChart';
export { Sparkline } from '../src/components/profile/charts/Sparkline';
export { MonthlyHeatmap } from '../src/components/profile/charts/MonthlyHeatmap';
export { StatGrid } from '../src/components/profile/panels/StatGrid';
export { HeroSection } from '../src/components/profile/panels/HeroSection';
export { AwardsPanel } from '../src/components/profile/panels/AwardsPanel';
export { JamesScoresPanel } from '../src/components/profile/panels/JamesScoresPanel';
export { SeasonLogPanel } from '../src/components/profile/panels/SeasonLogPanel';
export { SimilarPlayersPanel } from '../src/components/profile/panels/SimilarPlayersPanel';
export { SparklinePanel } from '../src/components/profile/panels/SparklinePanel';
export { CareerArcPanel } from '../src/components/profile/panels/CareerArcPanel';
export { ProfilePageSkeleton } from '../src/components/profile/ProfilePageSkeleton';

export { MobileChart } from '../src/mobile/components/MobileChart';
export { MobileMultiChart } from '../src/mobile/components/MobileMultiChart';
export { MobileTabBar } from '../src/mobile/components/MobileTabBar';
export { SeasonSheet } from '../src/mobile/components/SeasonSheet';

export type {
  ChartPlayer,
  ChartSeason,
  Metric,
  MetricId,
  XMode,
  PlayerAward,
  SimilarPlayer,
} from '../src/types';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 1000 * 60 * 5, retry: 1 } },
});

/**
 * Root wrapper every PCA screen needs: the React Query client, a router (for
 * the components that render `<Link>`), and the theme provider that writes the
 * active theme's CSS variables onto `<html>`. Mirrors the app's own
 * `main.tsx` + `App.tsx` setup, with an in-memory router.
 */
export function AppProviders({ children, initialPath = '/' }: { children: ReactNode; initialPath?: string }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <ThemeProvider>{children}</ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}
