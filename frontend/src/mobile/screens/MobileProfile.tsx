import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  useChartPlayer,
  usePlayerBundle,
  useSimilarPlayers,
  usePlayerAwards,
} from '../../hooks';
import { METRICS } from '../../constants';
import type { ChartSeason, MetricId } from '../../types';
import { careerWar, fmtMetric, peakSeason, sumMetric } from '../../utils/chart';
import { playerColor, colorTint } from '../../utils/color';
import { deriveTenures } from '../utils/tenures';
import { useSavedPlayers } from '../hooks/useSavedPlayers';
import { MobileChart } from '../components/MobileChart';
import { SeasonSheet } from '../components/SeasonSheet';
import { AnnotationGlyph } from '../../components/AnnotationGlyph';

const PIN_AT = 96; // px scrolled before the top bar pins/collapses

export function MobileProfile() {
  const { bbrefId } = useParams<{ bbrefId: string }>();
  const navigate = useNavigate();

  const { data: player, isLoading } = useChartPlayer(bbrefId ?? null, 0);
  const { data: bundle } = usePlayerBundle(bbrefId ?? null);
  const { data: similar } = useSimilarPlayers(bbrefId ?? null);
  const { data: awards = [] } = usePlayerAwards(bbrefId ?? null);
  const { isSaved, toggle } = useSavedPlayers();

  const [metric, setMetric] = useState<MetricId>('war');
  const [pinned, setPinned] = useState(false);
  const [sheetSeason, setSheetSeason] = useState<ChartSeason | null>(null);

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
    '--team-tint': colorTint(color, 0.1),
    '--team-glow': colorTint(color, 0.22),
  } as React.CSSProperties;

  const war = careerWar(player.seasons);
  const peak = peakSeason(player.seasons, 'war');
  const saved = isSaved(player.id);

  const availableMetrics = METRICS.filter(m => {
    if (m.id === 'era' || m.id === 'era_plus') return player.isPitcher;
    if (['hr', 'avg', 'ops', 'ops_plus'].includes(m.id)) return player.isBatter;
    return true;
  });

  const stats: { label: string; value: string }[] = [
    { label: 'Career WAR', value: war.toFixed(1) },
    { label: 'Peak WAR', value: peak ? peak.val.toFixed(1) : '—' },
    { label: 'Seasons', value: String(player.seasons.length) },
  ];
  if (player.isBatter) {
    stats.push({ label: 'HR', value: String(Math.round(sumMetric(player.seasons, 'hr') ?? 0)) });
    const avg = sumMetric(player.seasons, 'avg');
    stats.push({ label: 'AVG', value: avg != null ? fmtMetric('avg', avg) : '—' });
  }
  if (player.isPitcher) {
    const era = sumMetric(player.seasons, 'era');
    stats.push({ label: 'ERA', value: era != null ? fmtMetric('era', era) : '—' });
    stats.push({ label: 'SO', value: String(Math.round(sumMetric(player.seasons, 'so') ?? 0)) });
  }

  // Team for a given season (used by the season sheet + log rows).
  const teamForYear = (year: number) =>
    tenures.find(t => year >= t.startYear && year <= t.endYear)?.team ?? null;

  const similarList = [
    ...(similar?.batters ?? []),
    ...(similar?.pitchers ?? []),
  ].slice(0, 12);

  return (
    <div
      className="m-screen m-profile"
      style={cssVars}
      onScroll={e => setPinned(e.currentTarget.scrollTop > PIN_AT)}
    >
      <div className={`m-topbar ${pinned ? 'is-pinned' : ''}`}>
        <button className="m-back" onClick={() => navigate(-1)} aria-label="Back">‹</button>
        <span className="m-topbar-name">{player.name}</span>
        <button
          className={`m-follow-mini ${saved ? 'is-on' : ''}`}
          onClick={() => toggle({ bbref_id: player.id, name: player.name, pos: player.pos })}
          aria-label={saved ? 'Unfollow' : 'Follow'}
        >
          {saved ? '✓' : '+'}
        </button>
      </div>

      {/* hero */}
      <div className="m-hero">
        <div className="m-hero-head">
          <div className="m-hero-avatar" style={{ background: color }}>{player.initials}</div>
          <div className="m-hero-id">
            <div className="m-hero-eyebrow">{player.pos} · {player.years}</div>
            <h1 className="m-hero-name">{player.name}</h1>
          </div>
        </div>
        <button
          className={`m-follow ${saved ? 'is-on' : ''}`}
          onClick={() => toggle({ bbref_id: player.id, name: player.name, pos: player.pos })}
        >
          {saved ? '✓ Following' : '+ Follow'}
        </button>
      </div>

      {/* horizontal stat cards */}
      <div className="m-statcards">
        {stats.map(s => (
          <div key={s.label} className="m-statcard">
            <div className="m-statcard-val">{s.value}</div>
            <div className="m-statcard-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* career chart with metric tabs */}
      <section className="m-section">
        <div className="m-chiprow m-chiprow-scroll">
          {availableMetrics.map(m => (
            <button
              key={m.id}
              className={`m-chip ${metric === m.id ? 'is-active' : ''}`}
              onClick={() => setMetric(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>
        <div className="m-card">
          <MobileChart player={player} metric={metric} color={color} xMode="year" />
        </div>
      </section>

      {/* team timeline */}
      {tenures.length > 0 && (
        <section className="m-section">
          <h2 className="m-section-title">Teams</h2>
          <div className="m-timeline">
            {tenures.map((t, i) => (
              <div key={`${t.team}-${i}`} className="m-tenure">
                <span className="m-tenure-bar" style={{ background: t.color }} />
                <span className="m-tenure-team">{t.team}</span>
                <span className="m-tenure-years">
                  {t.startYear === t.endYear ? t.startYear : `${t.startYear}–${t.endYear}`}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* season log */}
      <section className="m-section">
        <h2 className="m-section-title">Season log</h2>
        <div className="m-log">
          {[...player.seasons].reverse().map(s => {
            const yearAwards = awards.filter(a => a.year === s.season);
            return (
              <button key={s.season} className="m-log-row" onClick={() => setSheetSeason(s)}>
                <span className="m-log-year">{s.season}</span>
                <span className="m-log-team">{teamForYear(s.season) ?? ''}</span>
                <span className="m-log-war">{s.war != null ? `${s.war.toFixed(1)}` : '—'}</span>
                <span className="m-log-awards">
                  {yearAwards.slice(0, 3).map(a => (
                    <AnnotationGlyph key={a.id} kind={a.kind} color={color} size={13} />
                  ))}
                </span>
                <span className="m-row-chev">›</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* awards */}
      {awards.length > 0 && (
        <section className="m-section">
          <h2 className="m-section-title">Awards & honors</h2>
          <div className="m-awards">
            {awards.map(a => (
              <span key={a.id} className="m-award" title={a.notes ?? undefined}>
                <AnnotationGlyph kind={a.kind} color={color} size={16} />
                <span className="m-award-yr">{a.year}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* similar players */}
      {similarList.length > 0 && (
        <section className="m-section">
          <h2 className="m-section-title">Similar players</h2>
          <div className="m-carousel">
            {similarList.map(sp => {
              const name = `${sp.first_name} ${sp.last_name}`;
              const c = playerColor(sp.bbref_id);
              return (
                <button
                  key={sp.bbref_id}
                  className="m-simcard"
                  onClick={() => navigate(`/player/${sp.bbref_id}`)}
                >
                  <span className="m-swatch" style={{ background: c }}>
                    {(sp.first_name[0] ?? '') + (sp.last_name[0] ?? '')}
                  </span>
                  <span className="m-simcard-name">{name}</span>
                  <span className="m-simcard-war">{sp.career_war.toFixed(0)} WAR</span>
                </button>
              );
            })}
          </div>
        </section>
      )}

      <p className="m-footer">
        Data: Baseball Reference · bWAR
        {bundle?.last_updated ? ` · Updated ${bundle.last_updated}` : ''}
      </p>

      <SeasonSheet
        player={player}
        season={sheetSeason}
        awards={awards}
        team={sheetSeason ? teamForYear(sheetSeason.season) : null}
        color={color}
        onClose={() => setSheetSeason(null)}
      />
    </div>
  );
}
