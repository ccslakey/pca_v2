import { AnnotationGlyph } from '../AnnotationGlyph';
import type { PlayerAward, AwardKind } from '../../types';

const AWARD_LABELS: Record<AwardKind, string> = {
  mvp:       'MVP',
  cy:        'Cy Young',
  roty:      'Rookie of the Year',
  gg:        'Gold Glove',
  ss:        'Silver Slugger',
  tc_b:      'Triple Crown (Batting)',
  tc_p:      'Triple Crown (Pitching)',
  hof:       'Hall of Fame',
  postmvp:   'Postseason MVP',
  bat_title: 'Batting Title',
  era_title: 'ERA Title',
  all_mlb:   'All-MLB Team',
  ws:        'World Series',
  asg:       'All-Star',
};

interface Props {
  awards: PlayerAward[];
  color:  string;
}

export function AwardsPanel({ awards, color }: Props) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">Awards &amp; milestones</div>
      </div>
      {awards.length === 0 ? (
        <div style={{ color: 'var(--text-3)', fontSize: 12, padding: '8px 4px' }}>
          No awards on record.
        </div>
      ) : (
        <div className="awards-list" style={{ marginTop: 8 }}>
          {awards.map((a) => {
            const label  = AWARD_LABELS[a.kind];
            const suffix = [a.league, a.notes].filter(Boolean).join(' · ');
            return (
              <div key={a.id} className="award-row">
                <div className="yr">{a.year}</div>
                <div className="glyph">
                  <svg width="14" height="14" viewBox="-7 -7 14 14">
                    <AnnotationGlyph kind={a.kind} color={color} />
                  </svg>
                </div>
                <div className="label">
                  {label}
                  {suffix && <span className="muted" style={{ marginLeft: 6 }}>{suffix}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
