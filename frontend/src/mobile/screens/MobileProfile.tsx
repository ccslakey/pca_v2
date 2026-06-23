import { useMemo, useRef, useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  useChartPlayer,
  usePlayerBundle,
  usePlayerDetail,
  useSimilarPlayers,
  usePlayerAwards,
} from '../../hooks';
import { METRICS } from '../../constants';
import type { ChartSeason, MetricId } from '../../types';
import { careerWar, fmtMetric, peakSeason, sumMetric } from '../../utils/chart';
import { playerColor, colorTint } from '../../utils/color';
import { initials } from '../../utils/format';
import { deriveTenures } from '../utils/tenures';
import { useSavedPlayers } from '../hooks/useSavedPlayers';
import { MobileChart } from '../components/MobileChart';
import { SeasonSheet } from '../components/SeasonSheet';
import { AnnotationGlyph } from '../../components/AnnotationGlyph';

export function MobileProfile() {
  const { bbrefId } = useParams<{ bbrefId: string }>();
  const navigate = useNavigate();

  const { data: player, isLoading } = useChartPlayer(bbrefId ?? null, 0);
  const { data: bundle } = usePlayerBundle(bbrefId ?? null);
  const { data: detail } = usePlayerDetail(bbrefId ?? null);
  const { data: similar } = useSimilarPlayers(bbrefId ?? null);
  const { data: awards = [] } = usePlayerAwards(bbrefId ?? null);
  const { isSaved, toggle } = useSavedPlayers();

  const [metric, setMetric] = useState<MetricId>('war');
  const [pinned, setPinned] = useState(false);
  const [sheetSeason, setSheetSeason] = useState<ChartSeason | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => setPinned(el.scrollTop > 90);
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [player]);

  const tenures = useMemo(
    () => (bundle ? deriveTenures(bundle.batting, bundle.pitching) : []),
    [bundle],
  );

  if (isLoading || !player) {
    return <div className="m-screen"><div className="m-empty">Loading…</div></div>;
  }

  const color = playerColor(player.id);
  const cssVars = {
    '--team-color': color,
    '--team-tint': colorTint(color, 0.12),
    '--team-glow': colorTint(color, 0.32),
  } as React.CSSProperties;

  const isPitcher = player.isPitcher;
  const careerWAR = careerWar(player.seasons);
  const careerHR = sumMetric(player.seasons, 'hr') ?? 0;
  const careerSO = sumMetric(player.seasons, 'so') ?? 0;
  const careerAVG = sumMetric(player.seasons, 'avg');
  const careerOPS = sumMetric(player.seasons, 'ops');
  const careerERA = isPitcher ? sumMetric(player.seasons, 'era') : null;
  const peakWAR = peakSeason(player.seasons, 'war');
  const peakSeasonYr = peakWAR?.season;
  const jersey = (player.id.charCodeAt(0) % 60) + 1;
  const saved = isSaved(player.id);

  const availableMetrics = METRICS.filter(m => {
    if (m.id === 'era' || m.id === 'era_plus') return isPitcher;
    if (['hr', 'avg', 'ops', 'ops_plus'].includes(m.id)) return player.isBatter;
    return true;
  });

  const metricVal = sumMetric(player.seasons, metric);
  const metricPeak = peakSeason(player.seasons, metric);
  const isCounting = ['war', 'hr', 'so'].includes(metric);

  const tlSpan = tenures.length
    ? { start: tenures[0].startYear, end: tenures[tenures.length - 1].endYear }
    : null;
  const teamForYear = (year: number) =>
    tenures.find(t => year >= t.startYear && year <= t.endYear) ?? null;

  const awardCount = awards.filter(a => ['mvp', 'cy', 'gg'].includes(a.kind)).length;
  const asgCount = awards.filter(a => a.kind === 'asg').length;

  const similarList = [...(similar?.batters ?? []), ...(similar?.pitchers ?? [])]
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 6);

  const goCompare = () => navigate(`/?compare=${player.id}`);

  return (
    <div className="m-screen" style={cssVars}>
      <div className={`m-topbar ${pinned ? 'is-pinned' : ''}`}>
        <button className="m-back" onClick={() => navigate(-1)} aria-label="Back">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <polyline points="15 6 9 12 15 18" />
          </svg>
        </button>
        <div className="m-topbar-title">
          {player.name}
          <span className="sub">{player.pos}</span>
        </div>
        <button className="m-topbar-action" title="Compare" onClick={goCompare}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </div>

      <div className="m-scroll" ref={scrollRef}>
        {/* Hero */}
        <div className="m-hero">
          <div className="m-hero-top">
            <div className="m-hero-shot" style={{ background: color }}>
              {initials(player.name)}
              <span className="m-hero-jersey">#{jersey}</span>
            </div>
            <div className="m-hero-text">
              <div className="m-hero-team">
                <span className="swatch" style={{ background: color }} />
                <span>{player.pos}</span>
              </div>
              <h1 className="m-hero-name">{player.name}</h1>
              <div className="m-hero-sub">
                <span><strong>{player.pos}</strong></span>
                <span className="sep">·</span>
                <span>{player.years}</span>
                <span className="sep">·</span>
                <span>{player.seasons.length} seasons</span>
                {(detail?.bats || detail?.throws) && (
                  <>
                    <span className="sep">·</span>
                    <span><strong>{detail?.bats ?? '–'}/{detail?.throws ?? '–'}</strong></span>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="m-hero-actions">
            <button className="m-btn" onClick={goCompare}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
              Compare
            </button>
            <button className={`m-btn ${saved ? 'is-primary' : ''}`} onClick={() => toggle({ bbref_id: player.id, name: player.name, pos: player.pos })}>
              {saved ? '✓ Following' : '+ Follow'}
            </button>
          </div>
        </div>

        {/* Headline stat cards */}
        <div className="m-stat-row">
          <div className="m-stat-card is-headline">
            <div className="lbl">Career WAR</div>
            <div className="val">{careerWAR.toFixed(1)}</div>
            {peakWAR && peakSeasonYr && (
              <div className="sub">peak {peakWAR.val.toFixed(1)} · '{String(peakSeasonYr).slice(2)}</div>
            )}
          </div>
          <div className="m-stat-card">
            <div className="lbl">Home Runs</div>
            <div className="val">{Math.round(careerHR)}</div>
            <div className="sub">{(careerHR / player.seasons.length).toFixed(1)} / yr</div>
          </div>
          {isPitcher ? (
            <div className="m-stat-card">
              <div className="lbl">ERA</div>
              <div className="val">{fmtMetric('era', careerERA)}</div>
              <div className="sub">{Math.round(careerSO)} K career</div>
            </div>
          ) : (
            <div className="m-stat-card">
              <div className="lbl">AVG / OPS</div>
              <div className="val">{fmtMetric('avg', careerAVG)}</div>
              <div className="sub">OPS {fmtMetric('ops', careerOPS)}</div>
            </div>
          )}
          <div className="m-stat-card">
            <div className="lbl">Strikeouts</div>
            <div className="val">{Math.round(careerSO)}</div>
            <div className="sub">{Math.round(careerSO / player.seasons.length)} / yr</div>
          </div>
          <div className="m-stat-card">
            <div className="lbl">Awards</div>
            <div className="val">{awardCount}</div>
            <div className="sub">{asgCount}× All-Star</div>
          </div>
        </div>

        {/* Career arc chart */}
        <div className="m-section">
          <div className="m-section-title">Career arc <span className="muted">by season</span></div>
          <span className="m-section-action">
            {player.seasons[0].age != null
              ? `age ${player.seasons[0].age}–${player.seasons[player.seasons.length - 1].age}`
              : ''}
          </span>
        </div>
        <div className="m-card">
          <div className="m-chart-tabs">
            {availableMetrics.map(m => (
              <button key={m.id} className={`m-chart-tab ${metric === m.id ? 'is-active' : ''}`} onClick={() => setMetric(m.id)}>
                {m.label}
              </button>
            ))}
          </div>
          <div className="m-chart-head">
            <div className="big">
              {fmtMetric(metric, metricVal)}
              <span className="unit">{isCounting ? 'career' : 'career avg'}</span>
            </div>
            {metricPeak && (
              <div className="peak">
                <strong>peak</strong> {fmtMetric(metric, metricPeak.val)}<br />
                <span style={{ opacity: 0.7 }}>
                  '{String(metricPeak.season).slice(2)}, age {player.seasons.find(s => s.season === metricPeak.season)?.age}
                </span>
              </div>
            )}
          </div>
          <MobileChart player={player} metric={metric} color={color} width={340} height={180} />
        </div>

        {/* Team timeline */}
        {tlSpan && (
          <>
            <div className="m-section">
              <div className="m-section-title">Team timeline <span className="muted">{tenures.length} {tenures.length === 1 ? 'team' : 'teams'}</span></div>
              <span className="m-section-action">{tlSpan.start}–{tlSpan.end}</span>
            </div>
            <div className="m-card">
              <svg className="m-tl-lane" viewBox="0 0 320 22" preserveAspectRatio="none">
                {tenures.map((t, i) => {
                  const total = tlSpan.end - tlSpan.start || 1;
                  const x = ((t.startYear - tlSpan.start) / total) * 320;
                  const w = ((t.endYear - t.startYear + 1) / total) * 320;
                  return <rect key={i} x={x} y={2} width={Math.max(2, w - 1)} height={18} rx={3} ry={3} fill={t.color} />;
                })}
              </svg>
              <div className="m-tl-axis">
                <span>{tlSpan.start}</span>
                <span>{tlSpan.end}</span>
              </div>
              <div className="m-timeline">
                {tenures.map((t, i) => (
                  <div key={i} className="tl-row">
                    <div className="tl-years">{t.startYear === t.endYear ? t.startYear : `${t.startYear}–${t.endYear}`}</div>
                    <div className="tl-bar-wrap">
                      <span className="tl-swatch" style={{ background: t.color }} />
                      <span className="tl-team">{t.team}</span>
                      <span className="tl-len">{t.endYear - t.startYear + 1}y</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Season log */}
        <div className="m-section">
          <div className="m-section-title">Season log <span className="muted">{player.seasons.length} seasons</span></div>
          <span className="m-section-action">tap a row</span>
        </div>
        <div className="m-card">
          <div className="m-seasons">
            {[...player.seasons].reverse().map(s => {
              const isPeak = s.season === peakSeasonYr;
              const sAnnots = awards.filter(a => a.year === s.season);
              const warW = Math.max(8, Math.min(100, ((s.war ?? 0) / Math.max(1, peakWAR?.val ?? 1)) * 100));
              const tm = teamForYear(s.season);
              return (
                <button key={s.season} className={`m-season ${isPeak ? 'is-peak' : ''}`} onClick={() => setSheetSeason(s)}>
                  <div className="m-season-year">
                    {s.season}
                    {s.age != null && <span className="age">age {s.age}</span>}
                  </div>
                  <div className="m-season-mid">
                    {tm && (
                      <span className="m-season-team">
                        <span className="dot" style={{ background: tm.color }} />
                        <span>{tm.team}</span>
                      </span>
                    )}
                    <div className="m-season-bar-wrap">
                      <div className="m-season-bar" style={{ width: `${warW}%` }} />
                    </div>
                  </div>
                  <div className="m-season-stats">
                    <div className="v">{s.war != null ? s.war.toFixed(1) : '—'}</div>
                    <div className="v2">
                      {isPitcher ? `${fmtMetric('era', s.era)} ERA` : fmtMetric('avg', s.avg)}
                      {sAnnots.length > 0 && (
                        <span className="m-season-annot">
                          {sAnnots.slice(0, 2).map(a => (
                            <span key={a.id} className="m-annot-pill" title={a.notes ?? a.kind}>
                              <AnnotationGlyph kind={a.kind} color={color} size={11} />
                            </span>
                          ))}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Awards */}
        <div className="m-section">
          <div className="m-section-title">Awards &amp; milestones <span className="muted">{awards.length}</span></div>
        </div>
        <div className="m-card">
          <div className="m-awards">
            {awards.length === 0 && (
              <div style={{ color: 'var(--text-3)', fontSize: 12, padding: '8px 4px', fontFamily: 'var(--font-mono)' }}>
                No notable awards recorded.
              </div>
            )}
            {[...awards].sort((a, b) => b.year - a.year).slice(0, 6).map(a => (
              <div key={a.id} className="m-award">
                <div className="yr">{a.year}</div>
                <div className="glyph">
                  <AnnotationGlyph kind={a.kind} color={color} size={14} />
                </div>
                <div className="label">
                  {a.notes ?? a.kind.toUpperCase()}
                  <span className="sub">age {player.seasons.find(s => s.season === a.year)?.age ?? '—'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Similar players */}
        {similarList.length > 0 && (
          <>
            <div className="m-section">
              <div className="m-section-title">Similar players <span className="muted">by WAR &amp; position</span></div>
              <span className="m-section-action">swipe →</span>
            </div>
            <div className="m-comp-row">
              {similarList.map(sp => {
                const c = playerColor(sp.bbref_id);
                const name = `${sp.first_name} ${sp.last_name}`;
                return (
                  <button
                    key={sp.bbref_id}
                    className="m-comp-card"
                    style={{ ['--accent-color' as string]: c }}
                    onClick={() => navigate(`/player/${sp.bbref_id}`)}
                  >
                    <div className="m-comp-head">
                      <div className="m-comp-shot" style={{ background: c }}>{initials(name)}</div>
                      <div style={{ minWidth: 0 }}>
                        <div className="m-comp-name">{name}</div>
                        <div className="m-comp-meta">{sp.primary_position ?? (sp.is_pitcher ? 'P' : 'B')}</div>
                      </div>
                    </div>
                    <div className="m-comp-foot">
                      <div className="big">{sp.career_war.toFixed(1)}<span className="l">WAR</span></div>
                      <div className="sim">{Math.round(sp.similarity)}%</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </>
        )}

        <div className="m-scroll-pad" />
      </div>

      <SeasonSheet
        player={player}
        season={sheetSeason}
        awards={awards}
        team={sheetSeason ? teamForYear(sheetSeason.season)?.team ?? null : null}
        color={color}
        onClose={() => setSheetSeason(null)}
      />
    </div>
  );
}
