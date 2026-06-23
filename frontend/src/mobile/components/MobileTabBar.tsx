import { useLocation, useNavigate } from 'react-router-dom';

interface Tab {
  to: string;
  label: string;
  icon: JSX.Element;
  // a route is "active" when the pathname matches this prefix
  match: (path: string) => boolean;
}

const I = { width: 22, height: 22, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

const TABS: Tab[] = [
  {
    to: '/browse',
    label: 'Leaders',
    match: p => p.startsWith('/browse'),
    icon: (
      <svg {...I}><path d="M4 19V10M10 19V5M16 19v-7M22 19H2" /></svg>
    ),
  },
  {
    to: '/',
    label: 'Compare',
    // Compare owns the landing and the player profile drill-in
    match: p => p === '/' || p.startsWith('/player'),
    icon: (
      <svg {...I}><path d="M3 6h7M3 12h12M3 18h5" /><circle cx="18" cy="6" r="2" /><circle cx="19" cy="18" r="2" /></svg>
    ),
  },
  {
    to: '/search',
    label: 'Search',
    match: p => p.startsWith('/search'),
    icon: (
      <svg {...I}><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
    ),
  },
  {
    to: '/saved',
    label: 'Saved',
    match: p => p.startsWith('/saved'),
    icon: (
      <svg {...I}><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>
    ),
  },
];

export function MobileTabBar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <nav className="m-tabbar" role="tablist">
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
            <span className="m-tab-icon">{t.icon}</span>
            <span className="m-tab-label">{t.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
