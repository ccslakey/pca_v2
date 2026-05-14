import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ParentSize } from '@visx/responsive';
import type { ChartPlayer, MetricId, XMode } from '../types';
import { useChartPlayer, useMeta } from '../hooks';
import { TopBar } from '../components/layout/TopBar';
import { ChipBar } from '../components/compare/ChipBar';
import { MetricToggle } from '../components/compare/MetricToggle';
import { CareerChart } from '../components/compare/CareerChart';
import { BrushChart } from '../components/compare/BrushChart';
import { PlayerCard } from '../components/compare/PlayerCard';
import { PlayerCardSkeleton } from '../components/compare/PlayerCardSkeleton';
import { ChartSkeleton } from '../components/compare/ChartSkeleton';
import { PlayerBrowser } from '../components/PlayerBrowser';

interface PlayerSlot {
  id: string;
  player: ChartPlayer | undefined;
  isLoading: boolean;
}

function useChartPlayers(selectedIds: string[]): PlayerSlot[] {
  const p0 = useChartPlayer(selectedIds[0] ?? null, 0);
  const p1 = useChartPlayer(selectedIds[1] ?? null, 1);
  const p2 = useChartPlayer(selectedIds[2] ?? null, 2);
  const p3 = useChartPlayer(selectedIds[3] ?? null, 3);
  const p4 = useChartPlayer(selectedIds[4] ?? null, 4);
  const p5 = useChartPlayer(selectedIds[5] ?? null, 5);
  const p6 = useChartPlayer(selectedIds[6] ?? null, 6);
  const p7 = useChartPlayer(selectedIds[7] ?? null, 7);
  const p8 = useChartPlayer(selectedIds[8] ?? null, 8);
  const p9 = useChartPlayer(selectedIds[9] ?? null, 9);

  const all = [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9];

  return useMemo(() => selectedIds.map((id, i) => ({
    id,
    player: all[i]?.data,
    isLoading: all[i]?.isLoading ?? false,
  })),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [selectedIds.join(','), p0.data, p1.data, p2.data, p3.data, p4.data, p5.data, p6.data, p7.data, p8.data, p9.data, p0.isLoading, p1.isLoading, p2.isLoading, p3.isLoading, p4.isLoading, p5.isLoading, p6.isLoading, p7.isLoading, p8.isLoading, p9.isLoading]);
}

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
  const { data: meta } = useMeta();

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
            <ParentSize>
              {({ width }) => (
                <>
                  <CareerChart
                    players={players}
                    metric={metric}
                    xMode={xMode}
                    xRange={yearRange}
                    showGlyphs={showGlyphs}
                    hoverPlayerId={hoverPlayerId}
                    setHoverPlayerId={setHoverPlayerId}
                    width={width}
                  />
                  <BrushChart
                    players={players}
                    metric={metric}
                    xMode={xMode}
                    xRange={yearRange}
                    fullRange={fullRange}
                    setXRange={setYearRange}
                    width={width}
                  />
                </>
              )}
            </ParentSize>
          )}
        </div>

        {slots.length > 0 && (
          <div className="cards-row">
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
        )}

        <PlayerBrowser selectedIds={selectedIds} onSelect={addPlayer} />

        <p className="footer-note">
          Data: Baseball Reference · All WAR values are bWAR
          {meta?.last_updated ? ` · Updated ${meta.last_updated}` : ''}
        </p>
      </div>
    </div>
  );
}
