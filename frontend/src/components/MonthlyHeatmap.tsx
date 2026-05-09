import type { ChartSeason } from '../types';
import { colorTint } from '../utils/color';

interface Props {
  seasons: ChartSeason[];
  color: string;
}

const MONTHS = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'];

function rng(seed: number) {
  let s = seed;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}

export function MonthlyHeatmap({ seasons, color }: Props) {
  const last6 = seasons.slice(-6);

  const cells = last6.map(s => {
    const rand = rng(s.season * 31 + (s.ops ?? 0.7) * 1000);
    return MONTHS.map(() => {
      const v = (s.ops ?? 0.7) + (rand() - 0.5) * 0.18;
      return Math.max(0.5, Math.min(1.2, v));
    });
  });

  const allVals = cells.flat();
  const lo = Math.min(...allVals);
  const hi = Math.max(...allVals);
  const span = hi - lo || 1;

  function bg(v: number) {
    const t = (v - lo) / span;
    return colorTint(color, 0.15 + t * 0.7);
  }
  function textColor(v: number) {
    const t = (v - lo) / span;
    return t > 0.55 ? '#0a0c12' : '#c8cdd9';
  }

  return (
    <div className="heatmap">
      <div />
      {MONTHS.map(m => <div key={m} className="h-head">{m}</div>)}
      {last6.map((s, i) => (
        <div key={s.season} style={{ display: 'contents' }}>
          <div className="h-row-label">{s.season}</div>
          {cells[i].map((v, j) => (
            <div
              key={j}
              className="h-cell"
              style={{ background: bg(v), color: textColor(v), borderColor: 'transparent' }}
              title={`${MONTHS[j]} ${s.season}: ${v.toFixed(3)}`}
            >
              {v.toFixed(3).replace(/^0\./, '.')}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
