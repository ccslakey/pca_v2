import { lazy, Suspense } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ComparePage } from './pages/ComparePage';

// Lazy: only the landing route ships in the initial bundle. /browse and
// /player/:id are split into their own chunks (loaded on navigation).
const LeaderboardPage = lazy(() =>
  import('./pages/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })),
);
const ProfilePage = lazy(() =>
  import('./pages/ProfilePage').then(m => ({ default: m.ProfilePage })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={null}>
          <Routes>
            <Route path="/" element={<ComparePage />} />
            <Route path="/browse" element={<LeaderboardPage />} />
            <Route path="/player/:bbrefId" element={<ProfilePage />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
