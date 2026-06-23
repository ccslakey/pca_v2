import { useEffect } from 'react';
import type { ChartPlayer, ChartSeason, MetricId, PlayerAward } from '../../types';
import { fmtMetric } from '../../utils/chart';
import { teamColor } from '../utils/tenures';
import { AnnotationGlyph } from '../../components/AnnotationGlyph';

interface Props {
  player: ChartPlayer;
  season: ChartSeason | null;
  awards: PlayerAward[];
  team?: string | null;
  color: string;
  onClose: () => void;
}

const ROWS: { metric: MetricId; label: string }[] = [
  { metric: 'war', label: 'WAR' },
  { metric: 'era', label: 'ERA' },
  { metric: 'avg', label: 'AVG' },
  { metric: 'ops', label: 'OPS' },
  { metric: 'ops_plus', label: 'OPS+' },
  { metric: 'era_plus', label: 'ERA+' },
  { metric: 'hr', label: 'HR' },
  { metric: 'so', label: 'SO' },
];

/** Season-detail bottom sheet, ported from the comp's SeasonSheet. */
export function SeasonSheet({ player, season, awards, team, color, onClose }: Props) {
  useEffect(() => {
    if (!season) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [season, onClose]);

  if (!season) return null;

  const seasonAwards = awards.filter(a => a.year === season.season);
  const cells = ROWS.filter(r => (season[r.metric as keyof ChartSeason] as number | null) != null).slice(0, 6);

  return (
    <>
      <div className="m-sheet-scrim" onClick={onClose} role="presentation" />
      <div className="m-sheet m-fade-in" role="dialog" aria-modal="true" aria-label={`${player.name} ${season.season} season`}>
        <div className="m-sheet-handle" />
        <div className="m-sheet-head">
          <div>
            <div className="m-sheet-eyebrow">
              {season.season}
              {season.age != null ? ` · age ${season.age}` : ''}
            </div>
            <h2 className="m-sheet-title">{player.name}</h2>
            {team && (
              <div className="m-sheet-team">
                <span className="swatch" style={{ background: teamColor(team) }} />
                {team}
              </div>
            )}
          </div>
          <button className="m-sheet-close" onClick={onClose} aria-label="Close">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </button>
        </div>

        <div className="m-sheet-stats">
          {cells.map(r => (
            <div key={r.metric} className="m-sheet-stat">
              <div className="lbl">{r.label}</div>
              <div className="v">{fmtMetric(r.metric, season[r.metric as keyof ChartSeason] as number | null)}</div>
            </div>
          ))}
        </div>

        {seasonAwards.length > 0 && (
          <div className="m-sheet-notes">
            {seasonAwards.map(a => (
              <div key={a.id} className="m-sheet-note">
                <span className="glyph">
                  <AnnotationGlyph kind={a.kind} color={color} size={13} />
                </span>
                <span>{a.notes ?? a.kind.toUpperCase()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
