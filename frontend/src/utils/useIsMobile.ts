import { useEffect, useState } from 'react';

// 720px = $bp-md in styles/_breakpoints.scss — the primary mobile breakpoint.
// Below it we mount the dedicated native-app-style mobile shell instead of the
// responsive desktop pages.
const QUERY = '(max-width: 720px)';

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(QUERY).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(QUERY);
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener('change', onChange);
    // Sync once in case the viewport changed between render and effect.
    setIsMobile(mql.matches);
    return () => mql.removeEventListener('change', onChange);
  }, []);

  return isMobile;
}
