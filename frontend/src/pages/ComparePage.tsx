import { useState, useEffect, useMemo, lazy, Suspense } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { ChartPlayer, MetricId, XMode } from '../types';
import { useChartPlayers, useFeatured } from '../hooks';
import { TopBar } from '../components/layout/TopBar';
import { ChipBar } from '../components/compare/ChipBar';
import { MetricToggle } from '../components/compare/MetricToggle';
import { PlayerCard } from '../components/compare/PlayerCard';
import { PlayerCardSkeleton } from '../components/compare/PlayerCardSkeleton';
import { ChartSkeleton } from '../components/compare/ChartSkeleton';
import { FeaturedGallery } from '../components/compare/FeaturedGallery';
import { PlayerBrowser } from '../components/PlayerBrowser';

const ChartArea = lazy(() =>
  import('../components/compare/ChartArea').then(m => ({ default: m.ChartArea })),
);

export function ComparePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedIds, setSelectedIds] = useState<string[]>(() => {
    const raw = searchParams.get('compare');
    return raw ? raw.split(',').filter(Boolean) : [];
  });
  const [metric, setMetric] = useState<MetricId>('war');
  const [xMode, setXMode] = useState<XMode>('year');
  const [showGlyphs, setShowGlyphs] = useState(true);
  const [hoverPlayerId, setHoverPlayerId] = useState<string | null>(null);

  useEffect(() => {
    const url = selectedIds.length ? `/?compare=${selectedIds.join(',')}` : '/';
    navigate(url, { replace: true });
  }, [selectedIds]); // eslint-disable-line react-hooks/exhaustive-deps

  const slots = useChartPlayers(selectedIds);
  const players = useMemo(
    () => slots.filter(s => s.player).map(s => s.player as ChartPlayer),
    [slots],
  );
  const { data: featured } = useFeatured();

  // First-load: if URL has no ?compare=, auto-select a random featured trio.
  // hasInitialized guards against re-rolling when the user clears all players.
  const [hasInitialized, setHasInitialized] = useState(false);
  useEffect(() => {
    if (hasInitialized) return;
    if (selectedIds.length > 0) { setHasInitialized(true); return; }
    if (featured?.trios.length) {
      const trio = featured.trios[Math.floor(Math.random() * featured.trios.length)];
      setSelectedIds(trio.players.map(p => p.bbref_id));
      setHasInitialized(true);
    }
  }, [featured, hasInitialized, selectedIds.length]);

  const fullRange = useMemo<[number, number]>(() => {
    let lo = Infinity, hi = -Infinity;
    players.forEach(p => p.seasons.forEach(s => {
      const v = xMode === 'age' ? s.age : s.season;
      if (v == null) return;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }));
    return lo > hi ? (xMode === 'age' ? [18, 40] : [2000, 2024]) : [lo, hi];
  }, [players, xMode]);

  const [yearRange, setYearRange] = useState<[number, number]>(fullRange);

  useEffect(() => {
    setYearRange(fullRange);
  }, [fullRange[0], fullRange[1]]); // eslint-disable-line react-hooks/exhaustive-deps

  function addPlayer(id: string) {
    setSelectedIds(prev => prev.includes(id) ? prev : [...prev, id]);
  }

  function removePlayer(id: string) {
    setSelectedIds(prev => prev.filter(x => x !== id));
  }

  const isEmpty       = selectedIds.length === 0;
  const isInitialLoad = selectedIds.length > 0 && players.length === 0;

  return (
    <div className="app">
      <TopBar selectedIds={selectedIds} onSelect={addPlayer} />

      <div className="main">
      <ChipBar
        players={players}
        hoverPlayerId={hoverPlayerId}
        setHoverPlayerId={setHoverPlayerId}
        onRemove={removePlayer}
      />
        <MetricToggle metric={metric} onChange={setMetric} xMode={xMode} onXModeChange={setXMode} showGlyphs={showGlyphs} onToggleGlyphs={() => setShowGlyphs(v => !v)} />

        <div className="chart-card">
          {isEmpty ? (
            <div className="chart-empty">
              <div className="chart-empty-title">Add players to compare career arcs</div>
              <div className="chart-empty-sub">Search above or browse the leaderboard below · Up to 10 players</div>
            </div>
          ) : isInitialLoad ? (
            <ChartSkeleton />
          ) : (
            <Suspense fallback={<ChartSkeleton />}>
              <ChartArea
                players={players}
                metric={metric}
                xMode={xMode}
                xRange={yearRange}
                fullRange={fullRange}
                showGlyphs={showGlyphs}
                hoverPlayerId={hoverPlayerId}
                setHoverPlayerId={setHoverPlayerId}
                setXRange={setYearRange}
              />
            </Suspense>
          )}
        </div>

        {/* Always rendered (with reserved min-height when empty) so the auto-picked
            featured trio swap does not push FeaturedGallery / PlayerBrowser down. */}
        <div className="cards-row" style={{ minHeight: 96 }}>
          {slots.map(({ id, player }) =>
            player ? (
              <PlayerCard
                key={id}
                player={player}
                metric={metric}
                isHovered={hoverPlayerId === id}
                onHoverEnter={() => setHoverPlayerId(id)}
                onHoverLeave={() => setHoverPlayerId(null)}
                onRemove={() => removePlayer(id)}
              />
            ) : (
              <PlayerCardSkeleton key={id} />
            ),
          )}
        </div>

        <FeaturedGallery onSelect={setSelectedIds} />

        <PlayerBrowser selectedIds={selectedIds} onSelect={addPlayer} />

        <p className="footer-note">
          Data: Baseball Reference · All WAR values are bWAR
          {featured?.last_updated ? ` · Updated ${featured.last_updated}` : ''}
          {' · '}<a href="/methodology" style={{ color: 'inherit', opacity: 0.7 }}>Methodology</a>
        </p>
      </div>
    </div>
  );
}
