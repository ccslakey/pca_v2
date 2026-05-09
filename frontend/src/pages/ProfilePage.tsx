import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ParentSize } from '@visx/responsive';
import { useChartPlayer, useSimilarPlayers } from '../hooks';
import { ProfileChart } from '../components/ProfileChart';
import { Sparkline } from '../components/Sparkline';
import { MonthlyHeatmap } from '../components/MonthlyHeatmap';
import { AnnotationGlyph } from '../components/AnnotationGlyph';
import { METRICS } from '../constants';
import type { MetricId, ChartSeason } from '../types';
import { fmtMetric, peakSeason, careerWar } from '../utils/chart';
import { playerColor, colorTint } from '../utils/color';

function initials(name: string) {
  const parts = name.trim().split(' ');
  return parts.length >= 2
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function sumMetric(seasons: ChartSeason[], metric: MetricId): number | null {
  if (['war', 'hr', 'so'].includes(metric)) {
    return seasons.reduce((s, x) => s + (x[metric] ?? 0), 0);
  }
  const vals = seasons.map(s => s[metric]).filter((v): v is number => v != null);
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

export function ProfilePage() {
  const { bbrefId } = useParams<{ bbrefId: string }>();
  const [metric, setMetric] = useState<MetricId>('war');
  const [tab, setTab] = useState<'standard' | 'advanced'>('standard');

  const { data: player, isLoading } = useChartPlayer(bbrefId ?? null, 0);
  const { data: similar } = useSimilarPlayers(bbrefId ?? null);

  if (isLoading || !player) {
    return (
      <div className="profile" style={{ display: 'grid', placeItems: 'center', minHeight: '100vh' }}>
        <span style={{ color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>Loading…</span>
      </div>
    );
  }

  const color = playerColor(player.id);
  const cssVars = {
    '--team-color': color,
    '--team-tint': colorTint(color, 0.10),
    '--team-glow': colorTint(color, 0.22),
  } as React.CSSProperties;

  const war    = careerWar(player.seasons);
  const peak   = peakSeason(player.seasons, 'war');
  const careerHR  = sumMetric(player.seasons, 'hr') ?? 0;
  const careerSO  = sumMetric(player.seasons, 'so') ?? 0;
  const careerAVG = sumMetric(player.seasons, 'avg');
  const careerOPS = sumMetric(player.seasons, 'ops');
  const careerERA = sumMetric(player.seasons, 'era');

  const jerseyNum = (player.id.charCodeAt(0) % 60) + 1;
  const isPitcher = player.isPitcher && !player.isBatter;

  const availableMetrics = METRICS.filter(m => {
    if (m.id === 'era') return player.isPitcher;
    if (['hr', 'avg', 'ops'].includes(m.id)) return player.isBatter;
    return true;
  });

  return (
    <div className="profile" style={cssVars}>
      {/* Topbar */}
      <div className="topbar">
        <Link to="/" className="profile-back">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 6 9 12 15 18" />
          </svg>
          Comparison
        </Link>
        <div className="brand" style={{ marginLeft: 8 }}>
          <div className="brand-mark" />
          <span className="brand-name">Career Arc Visualizer</span>
        </div>
        <div style={{ flex: 1 }} />
        <div className="topbar-meta">
          <span className="dot" style={{ background: color, boxShadow: `0 0 10px ${colorTint(color, 0.7)}` }} />
          player profile · {player.id}
        </div>
      </div>

      <div className="profile-main">
        {/* Hero */}
        <div className="hero">
          <div className="hero-left">
            <div className="hero-headshot" style={{ background: color }}>
              {initials(player.name)}
              <span className="hero-jersey">#{jerseyNum}</span>
            </div>
          </div>
          <div className="hero-mid">
            <div className="hero-eyebrow">
              <span className="swatch" style={{ background: color }} />
              {player.pos} · {player.years}
            </div>
            <h1 className="hero-name">{player.name}</h1>
            <div className="hero-meta">
              <span><span className="label">Pos</span> {player.pos}</span>
              <span className="sep">·</span>
              <span><span className="label">Active</span> {player.years}</span>
              <span className="sep">·</span>
              <span><span className="label">Seasons</span> {player.seasons.length}</span>
              {peak && (
                <>
                  <span className="sep">·</span>
                  <span><span className="label">Peak WAR</span> {peak.val.toFixed(1)} ({peak.season})</span>
                </>
              )}
            </div>
          </div>
          <div className="hero-right hero-actions">
            <Link to={`/?compare=${player.id}`} className="btn">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
              Compare
            </Link>
          </div>
        </div>

        {/* Headline stats */}
        <div className="stat-grid">
          <div className="stat-block is-headline">
            <div className="stat-label">Career WAR</div>
            <div className="stat-value">{war.toFixed(1)}</div>
            {peak && <div className="stat-sub">Peak {peak.val.toFixed(1)} in {peak.season}</div>}
          </div>
          {player.isBatter && (
            <div className="stat-block">
              <div className="stat-label">Home Runs</div>
              <div className="stat-value">{careerHR}</div>
              <div className="stat-sub">{(careerHR / player.seasons.length).toFixed(1)} / yr</div>
            </div>
          )}
          {player.isBatter && (
            <div className="stat-block">
              <div className="stat-label">AVG / OPS</div>
              <div className="stat-value">{fmtMetric('avg', careerAVG)}</div>
              <div className="stat-sub">OPS {fmtMetric('ops', careerOPS)}</div>
            </div>
          )}
          {player.isPitcher && (
            <div className="stat-block">
              <div className="stat-label">ERA</div>
              <div className="stat-value">{fmtMetric('era', careerERA)}</div>
              <div className="stat-sub">{careerSO} K career</div>
            </div>
          )}
          <div className="stat-block">
            <div className="stat-label">{isPitcher ? 'Strikeouts' : 'Career SO'}</div>
            <div className="stat-value">{careerSO}</div>
            <div className="stat-sub">{player.seasons.length > 0 ? (careerSO / player.seasons.length).toFixed(0) : '—'} / yr</div>
          </div>
        </div>

        {/* 2-col body */}
        <div className="col-2">
          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Career arc chart */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  Career arc
                  <span className="muted">{METRICS.find(m => m.id === metric)?.full}</span>
                </div>
                <div className="metric-toggle" style={{ padding: 2 }}>
                  {availableMetrics.map(m => (
                    <button
                      key={m.id}
                      className={`metric-pill ${metric === m.id ? 'is-active' : ''}`}
                      style={{ padding: '4px 10px', fontSize: 11.5 }}
                      onClick={() => setMetric(m.id)}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
              <ParentSize>
                {({ width }) => width > 0 && (
                  <ProfileChart player={{ ...player, color }} metric={metric} width={width} height={280} />
                )}
              </ParentSize>
            </div>

            {/* By the numbers — sparkline grid */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  By the numbers
                  <span className="muted">all metrics, season by season</span>
                </div>
                {player.seasons[0] && (
                  <div className="panel-action">since {player.seasons[0].season}</div>
                )}
              </div>
              <div className="spark-grid">
                {availableMetrics.map(m => {
                  const series = player.seasons
                    .map(s => s[m.id])
                    .filter((v): v is number => v != null);
                  if (!series.length) return null;
                  const total = sumMetric(player.seasons, m.id);
                  const pk = peakSeason(player.seasons, m.id);
                  return (
                    <div key={m.id} className="spark">
                      <div className="spark-head">
                        <span className="spark-label">{m.label} · {m.full}</span>
                        <span className="spark-value">
                          {fmtMetric(m.id, total)}
                          {pk && (
                            <span className="spark-sub">
                              {['war', 'hr', 'so'].includes(m.id) ? 'career' : 'career avg'}
                              {' · '}peak {fmtMetric(m.id, pk.val)} '{String(pk.season).slice(2)}
                            </span>
                          )}
                        </span>
                      </div>
                      <Sparkline data={series} color={color} invert={m.id === 'era'} />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Season log table */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  Season log
                  <span className="muted">{player.seasons.length} seasons</span>
                </div>
                <div className="tabs">
                  <button
                    className={`tab ${tab === 'standard' ? 'is-active' : ''}`}
                    onClick={() => setTab('standard')}
                  >
                    Standard
                  </button>
                  <button
                    className={`tab ${tab === 'advanced' ? 'is-active' : ''}`}
                    onClick={() => setTab('advanced')}
                  >
                    Advanced
                  </button>
                </div>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="season-table">
                  <thead>
                    <tr>
                      <th className="year-col">Year</th>
                      <th>WAR</th>
                      {player.isBatter && <th>AVG</th>}
                      {player.isBatter && <th>HR</th>}
                      {player.isBatter && <th>OPS</th>}
                      {player.isPitcher && <th>ERA</th>}
                      {player.isPitcher && <th>SO</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {[...player.seasons].reverse().map(s => {
                      const isPeak = peak?.season === s.season;
                      const warWidth = Math.max(2, Math.min(80, ((s.war ?? 0) / 10) * 80));
                      return (
                        <tr key={s.season} className={isPeak ? 'is-peak' : ''}>
                          <td>{s.season}</td>
                          <td>
                            <span
                              className="micro-bar"
                              style={{ width: warWidth, background: color }}
                            />
                            {fmtMetric('war', s.war)}
                          </td>
                          {player.isBatter && <td>{fmtMetric('avg', s.avg)}</td>}
                          {player.isBatter && <td>{s.hr ?? '—'}</td>}
                          {player.isBatter && <td>{fmtMetric('ops', s.ops)}</td>}
                          {player.isPitcher && <td>{fmtMetric('era', s.era)}</td>}
                          {player.isPitcher && <td>{s.so ?? '—'}</td>}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Right column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Similar players */}
            {similar && similar.length > 0 && (
              <div className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    Similar players
                    <span className="muted">by WAR & position</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {similar.map(p => {
                    const c = playerColor(p.bbref_id);
                    const maxWar = Math.max(war, p.career_war, 1);
                    const sim = Math.max(40, Math.round(100 - (Math.abs(p.career_war - war) / maxWar) * 60));
                    return (
                      <Link key={p.bbref_id} to={`/player/${p.bbref_id}`} className="comp-row">
                        <div className="comp-shot" style={{ background: c }}>
                          {initials(`${p.first_name} ${p.last_name}`)}
                        </div>
                        <div className="comp-info">
                          <div className="comp-name">{p.first_name} {p.last_name}</div>
                          <div className="comp-meta">
                            {p.is_pitcher ? 'P' : 'B'} · {p.career_war.toFixed(1)} WAR
                            {p.mlb_played_first && ` · ${p.mlb_played_first}–${p.mlb_played_last ?? 'pres'}`}
                          </div>
                        </div>
                        <div className="comp-score">{sim}% sim</div>
                      </Link>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Monthly heatmap */}
            {player.isBatter && player.seasons.length >= 2 && (
              <div className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    Monthly OPS heatmap
                    <span className="muted">last 6 seasons</span>
                  </div>
                </div>
                <div className="heatmap-wrap">
                  <MonthlyHeatmap seasons={player.seasons} color={color} />
                </div>
              </div>
            )}

            {/* Awards placeholder — no annotation data yet */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Awards & milestones</div>
              </div>
              <div style={{ color: 'var(--text-3)', fontSize: 12, padding: '8px 4px' }}>
                Award data coming soon.
              </div>
              <div className="awards-list" style={{ marginTop: 8 }}>
                {[
                  { kind: 'mvp', label: 'MVP' },
                  { kind: 'cy', label: 'Cy Young' },
                  { kind: 'gg', label: 'Gold Glove' },
                  { kind: 'asg', label: 'All-Star' },
                  { kind: 'il', label: 'IL stint' },
                ].map(({ kind, label }) => (
                  <div key={kind} className="award-row" style={{ opacity: 0.35 }}>
                    <div className="yr">—</div>
                    <div className="glyph">
                      <svg width="14" height="14" viewBox="-7 -7 14 14">
                        <AnnotationGlyph
                          kind={kind as 'mvp' | 'cy' | 'gg' | 'asg' | 'il'}
                          color={kind === 'il' ? '#f87171' : color}
                        />
                      </svg>
                    </div>
                    <div className="label">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <p className="footer-note">
          Data: Baseball Reference · All WAR values are bWAR · {player.id}
        </p>
      </div>
    </div>
  );
}
