import { useEffect } from 'react';
import type { ChartPlayer, ChartSeason, PlayerAward } from '../../types';
import { fmtMetric } from '../../utils/chart';
import { AnnotationGlyph } from '../../components/AnnotationGlyph';

interface Props {
  player: ChartPlayer;
  season: ChartSeason | null;
  awards: PlayerAward[];
  team?: string | null;
  color: string;
  onClose: () => void;
}

const ROWS: { metric: Parameters<typeof fmtMetric>[0]; label: string }[] = [
  { metric: 'war', label: 'WAR' },
  { metric: 'hr', label: 'HR' },
  { metric: 'avg', label: 'AVG' },
  { metric: 'ops', label: 'OPS' },
  { metric: 'ops_plus', label: 'OPS+' },
  { metric: 'era', label: 'ERA' },
  { metric: 'era_plus', label: 'ERA+' },
  { metric: 'so', label: 'SO' },
];

/** Bottom sheet showing one season's detail. Tap outside or the handle to close. */
export function SeasonSheet({ player, season, awards, team, color, onClose }: Props) {
  useEffect(() => {
    if (!season) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [season, onClose]);

  if (!season) return null;

  const seasonAwards = awards.filter(a => a.year === season.season);
  const rows = ROWS.filter(r => (season[r.metric as keyof ChartSeason] as number | null) != null);

  return (
    <div className="m-sheet-backdrop" onClick={onClose} role="presentation">
      <div
        className="m-sheet"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={`${player.name} ${season.season} season`}
      >
        <div className="m-sheet-handle" />
        <div className="m-sheet-head">
          <div>
            <div className="m-sheet-year" style={{ color }}>{season.season}</div>
            <div className="m-sheet-sub">
              {player.name}
              {season.age != null ? ` · Age ${season.age}` : ''}
              {team ? ` · ${team}` : ''}
            </div>
          </div>
          <button type="button" className="m-sheet-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {seasonAwards.length > 0 && (
          <div className="m-sheet-awards">
            {seasonAwards.map(a => (
              <span key={a.id} className="m-sheet-award" title={a.notes ?? a.kind}>
                <AnnotationGlyph kind={a.kind} color={color} size={16} />
              </span>
            ))}
          </div>
        )}

        <div className="m-sheet-stats">
          {rows.map(r => (
            <div key={r.metric} className="m-sheet-stat">
              <span className="m-sheet-stat-label">{r.label}</span>
              <span className="m-sheet-stat-val">
                {fmtMetric(r.metric, season[r.metric as keyof ChartSeason] as number | null)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
