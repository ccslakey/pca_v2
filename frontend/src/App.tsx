import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ComparePage } from './pages/ComparePage';
import { ProfilePage } from './pages/ProfilePage';

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
        <Routes>
          <Route path="/" element={<ComparePage />} />
          <Route path="/player/:bbrefId" element={<ProfilePage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
