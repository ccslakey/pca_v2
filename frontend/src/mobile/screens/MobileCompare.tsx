import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useChartPlayers, usePlayerSearch, useFeatured } from '../../hooks';
import type { ChartPlayer, MetricId } from '../../types';
import { fmtMetric, isLowerBetter, peakSeason, sumMetric } from '../../utils/chart';
import { MobileMultiChart } from '../components/MobileMultiChart';

const METRIC_OPTS: { id: MetricId; label: string }[] = [
  { id: 'war', label: 'WAR' },
  { id: 'hr', label: 'HR' },
  { id: 'avg', label: 'AVG' },
  { id: 'ops', label: 'OPS' },
];

const lastName = (name: string) => name.split(' ').slice(-1)[0] || name;

export function MobileCompare() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [selectedIds, setSelectedIds] = useState<string[]>(() => {
    const raw = searchParams.get('compare');
    return raw ? raw.split(',').filter(Boolean) : [];
  });
  const [metric, setMetric] = useState<MetricId>('war');
  const [focusId, setFocusId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [query, setQuery] = useState('');

  useEffect(() => {
    const url = selectedIds.length ? `/?compare=${selectedIds.join(',')}` : '/';
    navigate(url, { replace: true });
  }, [selectedIds]); // eslint-disable-line react-hooks/exhaustive-deps

  const slots = useChartPlayers(selectedIds);
  const players = useMemo(
    () => slots.filter(s => s.player).map(s => s.player as ChartPlayer),
    [slots],
  );

  // Seed a featured trio on first load with an empty URL.
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
    setSelectedIds(prev => (prev.includes(id) || prev.length >= 5 ? prev : [...prev, id]));
    setQuery('');
    setAdding(false);
  }
  function removePlayer(id: string) {
    setSelectedIds(prev => prev.filter(x => x !== id));
    if (focusId === id) setFocusId(null);
  }
  const toggleFocus = (id: string) => setFocusId(f => (f === id ? null : id));

  const ranked = useMemo(
    () =>
      players
        .map(p => ({ p, total: sumMetric(p.seasons, metric), peak: peakSeason(p.seasons, metric) }))
        .sort((a, b) => {
          if (a.total == null) return 1;
          if (b.total == null) return -1;
          return isLowerBetter(metric) ? a.total - b.total : b.total - a.total;
        }),
    [players, metric],
  );

  const ages = players.flatMap(p => p.seasons.map(s => s.age).filter((a): a is number => a != null));
  const focusedName = focusId ? players.find(p => p.id === focusId)?.name : null;
  const metricLabel = METRIC_OPTS.find(m => m.id === metric)?.label ?? metric.toUpperCase();

  return (
    <div className="m-screen">
      <div className="m-topbar is-pinned">
        <div className="m-brand">
          <span className="mark" />
          <span className="name">Compare<span className="sub">{players.length} players</span></span>
        </div>
        <button className="m-topbar-action" title="Add player" onClick={() => setAdding(a => !a)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
        </button>
      </div>

      <div className="m-scroll">
        {/* Comparison set */}
        <div className="m-cmp-set" style={{ paddingTop: 12 }}>
          {players.map(p => (
            <span key={p.id} className="m-cmp-chip">
              <span className="sw" style={{ background: p.color }} />
              <span className="nm">{lastName(p.name)}</span>
              <button className="x" onClick={() => removePlayer(p.id)} aria-label={`Remove ${p.name}`}>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M6 6l12 12M18 6L6 18" /></svg>
              </button>
            </span>
          ))}
          {players.length < 5 && (
            <button className="m-cmp-chip add" onClick={() => setAdding(a => !a)}>+ Add</button>
          )}
        </div>

        {adding && (
          <div className="m-cmp-add">
            <input
              autoFocus
              placeholder="Search players to add…"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            {query.trim() && (search?.results?.length ?? 0) > 0 && (
              <div className="m-cmp-results">
                {search!.results.slice(0, 8).map(r => (
                  <button key={r.bbref_id} className="m-cmp-result" onClick={() => addPlayer(r.bbref_id)}>
                    {r.first_name} {r.last_name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Metric switch */}
        <div className="m-cmp-metric">
          {METRIC_OPTS.map(m => (
            <button key={m.id} className={metric === m.id ? 'is-active' : ''} onClick={() => setMetric(m.id)}>
              {m.label}
            </button>
          ))}
        </div>

        {players.length === 0 ? (
          <div className="m-empty">Add players to compare career arcs.</div>
        ) : (
          <>
            <div className="m-section">
              <div className="m-section-title">Career arc <span className="muted">{metricLabel} by age</span></div>
              <span className="m-section-action">tap a name</span>
            </div>
            <div className="m-card">
              <div className="m-cmp-charthead">
                <div className="t">{focusedName ?? `${players.length} players overlaid`}</div>
                {ages.length > 0 && <div className="x">age {Math.min(...ages)}–{Math.max(...ages)}</div>}
              </div>
              <MobileMultiChart players={players} metric={metric} focusId={focusId} />
              <div className="m-cmp-legend">
                {ranked.map(({ p, total }) => {
                  const cls = focusId ? (focusId === p.id ? 'is-focus' : 'is-dim') : '';
                  return (
                    <button key={p.id} className={`m-cmp-leg ${cls}`} onClick={() => toggleFocus(p.id)}>
                      <span className="sw" style={{ background: p.color }} />
                      {lastName(p.name)}
                      <span className="v">{fmtMetric(metric, total)}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="m-section">
              <div className="m-section-title">Ranked <span className="muted">by {metricLabel}</span></div>
              <span className="m-section-action">tap to highlight</span>
            </div>
            <div className="m-card" style={{ background: 'transparent', border: 'none', padding: '0 16px' }}>
              <div className="m-cmp-rank">
                {ranked.map(({ p, total, peak }, i) => (
                  <button
                    key={p.id}
                    className={`m-cmp-rrow ${focusId === p.id ? 'is-focus' : ''}`}
                    style={{ ['--c' as string]: p.color }}
                    onClick={() => toggleFocus(p.id)}
                    onDoubleClick={() => navigate(`/player/${p.id}`)}
                  >
                    <div className="rk">{i + 1}</div>
                    <div style={{ minWidth: 0 }}>
                      <div className="nm">{p.name}</div>
                      <div className="mt">{p.pos} · {p.years}</div>
                    </div>
                    <div className="val">
                      <div className="v">{fmtMetric(metric, total)}</div>
                      {peak && <div className="pk">peak {fmtMetric(metric, peak.val)}</div>}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        <div className="m-scroll-pad" />
      </div>
    </div>
  );
}
