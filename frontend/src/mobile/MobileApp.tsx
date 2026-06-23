import { Routes, Route, Navigate } from 'react-router-dom';
import { MobileTabBar } from './components/MobileTabBar';
import { MobileCompare } from './screens/MobileCompare';
import { MobileLeaders } from './screens/MobileLeaders';
import { MobileSearch } from './screens/MobileSearch';
import { MobileSaved } from './screens/MobileSaved';
import { MobileProfile } from './screens/MobileProfile';

/**
 * Native-app-style mobile shell, mounted below 720px (see App.tsx). Owns its
 * own <Routes> over the shared BrowserRouter so deep links resolve in either
 * mode. /search and /saved are mobile-only; everything else aligns with the
 * desktop paths.
 */
export function MobileApp() {
  return (
    <div className="m-app">
      <div className="m-stack">
        <Routes>
          <Route path="/" element={<MobileCompare />} />
          <Route path="/browse" element={<MobileLeaders />} />
          <Route path="/search" element={<MobileSearch />} />
          <Route path="/saved" element={<MobileSaved />} />
          <Route path="/player/:bbrefId" element={<MobileProfile />} />
          {/* Methodology pages aren't part of the mobile shell — send them home. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      <MobileTabBar />
    </div>
  );
}
