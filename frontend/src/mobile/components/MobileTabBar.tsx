import type { ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

interface Tab {
  to: string;
  label: string;
  icon: ReactNode;
  match: (path: string) => boolean;
}

// Icons ported from the comp's TabBar (Leaders · Compare · Search · Saved).
const TABS: Tab[] = [
  {
    to: '/browse',
    label: 'Leaders',
    match: p => p.startsWith('/browse'),
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 21h18M6 21V11M12 21V5M18 21v-7" />
      </svg>
    ),
  },
  {
    to: '/',
    label: 'Compare',
    // Compare owns the landing and the player-profile drill-in.
    match: p => p === '/' || p.startsWith('/player'),
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="3 15 8 9 13 12 21 5" />
        <polyline points="3 20 8 16 13 18 21 13" opacity="0.45" />
      </svg>
    ),
  },
  {
    to: '/search',
    label: 'Search',
    match: p => p.startsWith('/search'),
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-4.3-4.3" />
      </svg>
    ),
  },
  {
    to: '/saved',
    label: 'Saved',
    match: p => p.startsWith('/saved'),
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" />
      </svg>
    ),
  },
];

export function MobileTabBar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <div className="m-tabbar" role="tablist">
      {TABS.map(t => {
        const active = t.match(pathname);
        return (
          <button
            key={t.to}
            type="button"
            role="tab"
            aria-selected={active}
            className={`m-tab ${active ? 'is-active' : ''}`}
            onClick={() => navigate(t.to)}
          >
            {t.icon}
            <span>{t.label}</span>
          </button>
        );
      })}
    </div>
  );
}
