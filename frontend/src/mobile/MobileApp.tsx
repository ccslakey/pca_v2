import { Routes, Route, Navigate } from 'react-router-dom';
import { MobileTabBar } from './components/MobileTabBar';
import { MobileCompare } from './screens/MobileCompare';
import { MobileLeaders } from './screens/MobileLeaders';
import { MobileSearch } from './screens/MobileSearch';
import { MobileSaved } from './screens/MobileSaved';
import { MobileProfile } from './screens/MobileProfile';

/**
 * Native-app-style mobile shell, mounted below 720px (see App.tsx). Each screen
 * provides its own `.m-scroll` / `.m-screen` and is a direct flex child of
 * `.m-app`, so the floating tab bar and bottom sheet can position against it.
 * Owns its own <Routes> over the shared BrowserRouter so deep links resolve.
 */
export function MobileApp() {
  return (
    <div className="m-app">
      <Routes>
        <Route path="/" element={<MobileCompare />} />
        <Route path="/browse" element={<MobileLeaders />} />
        <Route path="/search" element={<MobileSearch />} />
        <Route path="/saved" element={<MobileSaved />} />
        <Route path="/player/:bbrefId" element={<MobileProfile />} />
        {/* Methodology pages aren't part of the mobile shell — send them home. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <MobileTabBar />
    </div>
  );
}
