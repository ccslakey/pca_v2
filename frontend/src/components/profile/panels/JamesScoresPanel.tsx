import '../panel.scss';
import './styles/JamesScoresPanel.scss';
import type { JamesScore } from '../../../types';

interface Props {
  james: JamesScore;
  isBatter: boolean;
  isPitcher: boolean;
}

function hofBadge(score: number): 'lock' | 'likely' | null {
  if (score >= 130) return 'lock';
  if (score >= 100) return 'likely';
  return null;
}

function ScoreBlock({ label, value, isMonitor }: {
  label: string;
  value: number;
  isMonitor?: boolean;
}) {
  const badge = isMonitor ? hofBadge(value) : null;
  return (
    <div className="james-block">
      <div className="james-label">{label}</div>
      <div className="james-value">{value}</div>
      {badge && <div className={`james-badge james-badge--${badge}`}>{badge}</div>}
    </div>
  );
}

export function JamesScoresPanel({ james, isBatter, isPitcher }: Props) {
  const hasBat = isBatter && (james.hof_monitor_bat > 0 || james.black_ink_bat > 0);
  const hasPit = isPitcher && (james.hof_monitor_pit > 0 || james.black_ink_pit > 0);

  if (!hasBat && !hasPit) return null;

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          Hall of Fame Metrics
          <span className="muted">Bill James</span>
        </div>
      </div>

      {hasBat && (
        <>
          {hasPit && <div className="james-role-label">Batting</div>}
          <div className="james-grid">
            <ScoreBlock label="HOF Monitor" value={james.hof_monitor_bat} isMonitor />
            <ScoreBlock label="Black Ink" value={james.black_ink_bat} />
            <ScoreBlock label="Gray Ink" value={james.gray_ink_bat} />
          </div>
        </>
      )}

      {hasPit && (
        <>
          <div className={`james-role-label${hasBat ? ' james-role-label--pit' : ''}`}>
            {hasBat ? 'Pitching' : ''}
          </div>
          <div className="james-grid">
            <ScoreBlock label="HOF Monitor" value={james.hof_monitor_pit} isMonitor />
            <ScoreBlock label="Black Ink" value={james.black_ink_pit} />
            <ScoreBlock label="Gray Ink" value={james.gray_ink_pit} />
          </div>
        </>
      )}

      <div className="james-legend">
        HOF Monitor: 100 = HOF avg · 130+ = lock
      </div>
    </div>
  );
}
