import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useChartPlayers, usePlayerSearch, useFeatured } from '../../hooks';
import type { ChartPlayer, ChartSeason, MetricId } from '../../types';
import { fmtMetric, isLowerBetter, peakSeason, sumMetric } from '../../utils/chart';
import { MobileMultiChart } from '../components/MobileMultiChart';
import { MobileChart } from '../components/MobileChart';
import { Sparkline } from '../../components/profile/charts/Sparkline';

type Layout = 'overlay' | 'focus' | 'multiples';

// Metrics offered on the segmented control (keep ERA out unless a pitcher is
// present, etc. is handled by availability below).
const METRIC_OPTS: { id: MetricId; label: string }[] = [
  { id: 'war', label: 'WAR' },
  { id: 'hr', label: 'HR' },
  { id: 'ops', label: 'OPS' },
  { id: 'ops_plus', label: 'OPS+' },
  { id: 'era', label: 'ERA' },
  { id: 'so', label: 'SO' },
];

function seriesValues(p: ChartPlayer, metric: MetricId): number[] {
  return p.seasons
    .map(s => s[metric as keyof ChartSeason] as number | null)
    .filter((v): v is number => v != null);
}

export function MobileCompare() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [selectedIds, setSelectedIds] = useState<string[]>(() => {
    const raw = searchParams.get('compare');
    return raw ? raw.split(',').filter(Boolean) : [];
  });
  const [metric, setMetric] = useState<MetricId>('war');
  const [layout, setLayout] = useState<Layout>('overlay');
  const [focusId, setFocusId] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  // Mirror selection into the URL so deep links + back button work.
  useEffect(() => {
    const url = selectedIds.length ? `/?compare=${selectedIds.join(',')}` : '/';
    navigate(url, { replace: true });
  }, [selectedIds]); // eslint-disable-line react-hooks/exhaustive-deps

  const slots = useChartPlayers(selectedIds);
  const players = useMemo(
    () => slots.filter(s => s.player).map(s => s.player as ChartPlayer),
    [slots],
  );

  // First load with an empty URL → seed a featured trio.
  const { data: featured } = useFeatured();
  const [seeded, setSeeded] = useState(false);
  useEffect(() => {
    if (seeded) return;
    if (selectedIds.length > 0) { setSeeded(true); return; }
    if (featured?.trios.length) {
      const trio = featured.trios[Math.floor(Math.random() * featured.trios.length)];
      setSelectedIds(trio.players.map(p => p.bbref_id));
      setSeeded(true);
    }
  }, [featured, seeded, selectedIds.length]);

  const { data: search } = usePlayerSearch(query.trim());

  function addPlayer(id: string) {
    setSelectedIds(prev => (prev.includes(id) || prev.length >= 10 ? prev : [...prev, id]));
    setQuery('');
  }
  function removePlayer(id: string) {
    setSelectedIds(prev => prev.filter(x => x !== id));
    if (focusId === id) setFocusId(null);
  }

  const focused = players.find(p => p.id === focusId) ?? players[0] ?? null;

  // Rank players by the active metric for the overlay leaderboard.
  const ranked = useMemo(() => {
    return [...players]
      .map(p => ({ p, val: sumMetric(p.seasons, metric) }))
      .sort((a, b) => {
        if (a.val == null) return 1;
        if (b.val == null) return -1;
        return isLowerBetter(metric) ? a.val - b.val : b.val - a.val;
      });
  }, [players, metric]);

  return (
    <div className="m-screen m-compare">
      <header className="m-screen-head">
        <h1 className="m-screen-title">Compare</h1>
      </header>

      {/* selected chips */}
      <div className="m-chiprow m-chiprow-scroll m-compare-chips">
        {players.map(p => (
          <span key={p.id} className="m-pchip" style={{ ['--c' as string]: p.color }}>
            <span className="m-pchip-dot" />
            {p.name.split(' ').slice(-1)[0]}
            <button className="m-pchip-x" onClick={() => removePlayer(p.id)} aria-label={`Remove ${p.name}`}>✕</button>
          </span>
        ))}
        {selectedIds.length === 0 && <span className="m-muted">Add players to compare</span>}
      </div>

      {/* add player search */}
      <div className="m-compare-add">
        <input
          className="m-search-input"
          placeholder={selectedIds.length >= 10 ? 'Max 10 players' : 'Add a player…'}
          value={query}
          onChange={e => setQuery(e.target.value)}
          disabled={selectedIds.length >= 10}
        />
        {query.trim() && (search?.results?.length ?? 0) > 0 && (
          <div className="m-compare-results">
            {search!.results.slice(0, 8).map(r => (
              <button key={r.bbref_id} className="m-compare-result" onClick={() => addPlayer(r.bbref_id)}>
                {r.first_name} {r.last_name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* metric segmented control */}
      <div className="m-chiprow m-chiprow-scroll">
        {METRIC_OPTS.map(m => (
          <button
            key={m.id}
            className={`m-chip ${metric === m.id ? 'is-active' : ''}`}
            onClick={() => setMetric(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* layout switcher */}
      <div className="m-seg">
        {(['overlay', 'focus', 'multiples'] as Layout[]).map(l => (
          <button
            key={l}
            className={`m-seg-btn ${layout === l ? 'is-active' : ''}`}
            onClick={() => setLayout(l)}
          >
            {l === 'overlay' ? 'Overlay' : l === 'focus' ? 'Focus' : 'Grid'}
          </button>
        ))}
      </div>

      {players.length === 0 ? (
        <div className="m-empty">Search above to start a comparison.</div>
      ) : layout === 'overlay' ? (
        <div className="m-card">
          <MobileMultiChart players={players} metric={metric} xMode="age" highlightId={focusId} />
          <ol className="m-rank">
            {ranked.map(({ p, val }, i) => (
              <li
                key={p.id}
                className={`m-rank-row ${focusId === p.id ? 'is-focus' : ''}`}
                onMouseEnter={() => setFocusId(p.id)}
                onClick={() => navigate(`/player/${p.id}`)}
              >
                <span className="m-rank-n">{i + 1}</span>
                <span className="m-rank-dot" style={{ background: p.color }} />
                <span className="m-rank-name">{p.name}</span>
                <span className="m-rank-val">{fmtMetric(metric, val)}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : layout === 'focus' && focused ? (
        <div className="m-card">
          <div className="m-focus-head">
            <span className="m-rank-dot" style={{ background: focused.color }} />
            <span className="m-focus-name">{focused.name}</span>
            <button className="m-focus-open" onClick={() => navigate(`/player/${focused.id}`)}>Open ›</button>
          </div>
          <MobileChart player={focused} metric={metric} color={focused.color} xMode="age" />
          <div className="m-rail">
            {players.map(p => {
              const vals = seriesValues(p, metric);
              return (
                <button
                  key={p.id}
                  className={`m-rail-item ${focused.id === p.id ? 'is-active' : ''}`}
                  onClick={() => setFocusId(p.id)}
                >
                  <div className="m-rail-top">
                    <span className="m-rank-dot" style={{ background: p.color }} />
                    <span className="m-rail-name">{p.name.split(' ').slice(-1)[0]}</span>
                  </div>
                  <div className="m-rail-spark">
                    {vals.length > 1
                      ? <Sparkline data={vals} color={p.color} height={28} invert={isLowerBetter(metric)} />
                      : <span className="m-muted">—</span>}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="m-multiples">
          {players.map(p => {
            const peak = peakSeason(p.seasons, metric);
            return (
              <div key={p.id} className="m-card m-multiple" onClick={() => navigate(`/player/${p.id}`)}>
                <div className="m-multiple-head">
                  <span className="m-rank-dot" style={{ background: p.color }} />
                  <span className="m-multiple-name">{p.name}</span>
                  {peak && <span className="m-multiple-peak">{fmtMetric(metric, peak.val)}</span>}
                </div>
                <MobileChart player={p} metric={metric} color={p.color} xMode="age" height={140} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
