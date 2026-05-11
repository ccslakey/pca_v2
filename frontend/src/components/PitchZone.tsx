import { useState } from 'react';
import { usePitchZone } from '../hooks';
import type { ZoneOutcome, ZoneRole } from '../types';

interface Props {
  bbrefId:   string;
  isBatter:  boolean;
  isPitcher: boolean;
  color:     string;
}

const X_MIN = -2.0;
const X_MAX =  2.0;
const Z_MIN =  0.5;
const Z_MAX =  5.0;

const SZ_X_MIN = -0.83;
const SZ_X_MAX =  0.83;
const SZ_Z_MIN =  1.5;
const SZ_Z_MAX =  3.5;

const GRID      = 20;
const WIDTH     = 280;
const HEIGHT    = 315;
const MIN_TOTAL = 10;

type RGB = [number, number, number];

const LAYERS: { threshold: number; rgb: RGB; blur: number; opacity: number }[] = [
  { threshold: 0.12, rgb: [35,  65, 180], blur: 26, opacity: 0.75 },
  { threshold: 0.28, rgb: [80,  60, 170], blur: 20, opacity: 0.75 },
  { threshold: 0.48, rgb: [160, 65, 120], blur: 14, opacity: 0.78 },
  { threshold: 0.65, rgb: [200, 65,  65], blur:  4, opacity: 0.82 },
  { threshold: 0.82, rgb: [175, 28,  28], blur:  2, opacity: 0.90 },
];

const BATTER_OUTCOMES:  { id: ZoneOutcome; label: string }[] = [
  { id: 'contact', label: 'Contact' },
  { id: 'hits',    label: 'Hits' },
  { id: 'whiffs',  label: 'Whiffs' },
];
const PITCHER_OUTCOMES: { id: ZoneOutcome; label: string }[] = [
  { id: 'whiffs',  label: 'Whiffs' },
  { id: 'contact', label: 'Contact' },
  { id: 'hits',    label: 'Hits' },
];

function toSvgX(ft: number) { return ((ft - X_MIN) / (X_MAX - X_MIN)) * WIDTH;  }
function toSvgZ(ft: number) { return ((Z_MAX - ft)  / (Z_MAX - Z_MIN)) * HEIGHT; }

export function PitchZone({ bbrefId, isBatter, isPitcher, color }: Props) {
  const isTwoWay = isBatter && isPitcher;
  const [role,    setRole]    = useState<ZoneRole>(isBatter ? 'B' : 'P');
  const outcomes = role === 'P' ? PITCHER_OUTCOMES : BATTER_OUTCOMES;
  const [outcome, setOutcome] = useState<ZoneOutcome>(outcomes[0].id);

  // Reset outcome when role changes so we don't show a stale tab highlight
  function handleRoleChange(r: ZoneRole) {
    setRole(r);
    setOutcome(r === 'P' ? PITCHER_OUTCOMES[0].id : BATTER_OUTCOMES[0].id);
  }

  const { data, isLoading } = usePitchZone(bbrefId, role, outcome);

  const cellW = WIDTH  / GRID;
  const cellH = HEIGHT / GRID;

  const grid = new Map<string, { count: number; total: number }>();
  if (data?.buckets) {
    for (const b of data.buckets) {
      const cx = Math.floor(((b.plate_x - X_MIN) / (X_MAX - X_MIN)) * GRID);
      const cz = Math.floor(((Z_MAX - b.plate_z) / (Z_MAX - Z_MIN)) * GRID);
      if (cx < 0 || cx >= GRID || cz < 0 || cz >= GRID) continue;
      const key = `${cx},${cz}`;
      const prev = grid.get(key) ?? { count: 0, total: 0 };
      grid.set(key, { count: prev.count + b.count, total: prev.total + b.total });
    }
  }

  const rates: number[] = [];
  for (const { count, total } of grid.values()) {
    if (total >= MIN_TOTAL) rates.push(count / total);
  }
  const lo   = rates.length ? Math.min(...rates) : 0;
  const span = rates.length ? Math.max(...rates) - lo : 1;

  const szX1 = toSvgX(SZ_X_MIN);
  const szX2 = toSvgX(SZ_X_MAX);
  const szZ1 = toSvgZ(SZ_Z_MAX);
  const szZ2 = toSvgZ(SZ_Z_MIN);

  const uid     = `${bbrefId}-${role}`;
  const clipId  = `zone-clip-${uid}`;
  const hasData = !isLoading && data && data.buckets.length > 0;

  return (
    <div className="pitch-zone-wrap">

      {/* Role tabs — only shown for two-way players */}
      {isTwoWay && (
        <div className="pitch-zone-tabs" style={{ marginBottom: 4 }}>
          {([{ id: 'B', label: 'Batting' }, { id: 'P', label: 'Pitching' }] as const).map(r => (
            <button
              key={r.id}
              className={`pitch-zone-tab${role === r.id ? ' active' : ''}`}
              onClick={() => handleRoleChange(r.id)}
            >
              {r.label}
            </button>
          ))}
        </div>
      )}

      {/* Outcome tabs */}
      <div className="pitch-zone-tabs">
        {outcomes.map(o => (
          <button
            key={o.id}
            className={`pitch-zone-tab${outcome === o.id ? ' active' : ''}`}
            onClick={() => setOutcome(o.id)}
          >
            {o.label}
          </button>
        ))}
      </div>

      <div style={{ position: 'relative' }}>
        <svg width={WIDTH} height={HEIGHT} style={{ display: 'block' }}>
          <defs>
            {/* Clip to SVG bounds so blurred blobs don't overflow */}
            <clipPath id={clipId}>
              <rect width={WIDTH} height={HEIGHT} />
            </clipPath>

            {LAYERS.map((_, i) => (
              <filter key={i} id={`zone-blur-${uid}-${i}`}
                      x="-60%" y="-60%" width="220%" height="220%">
                <feGaussianBlur stdDeviation={LAYERS[i].blur} />
              </filter>
            ))}
          </defs>

          <rect width={WIDTH} height={HEIGHT} fill="var(--bg-deep, #080a0f)" rx={6} />

          {/* All heat layers, clipped to SVG bounds */}
          <g clipPath={`url(#${clipId})`}>
            {hasData && LAYERS.map((layer, i) => {
              const minRate = lo + layer.threshold * span;
              const cells = [...grid.entries()].filter(([, { count, total }]) =>
                total >= MIN_TOTAL && count / total >= minRate
              );
              if (!cells.length) return null;
              const [r, g, b] = layer.rgb;
              return (
                <g key={i} filter={`url(#zone-blur-${uid}-${i})`} opacity={layer.opacity}>
                  {cells.map(([key]) => {
                    const [cx, cz] = key.split(',').map(Number);
                    return (
                      <rect
                        key={key}
                        x={cx * cellW} y={cz * cellH}
                        width={cellW}  height={cellH}
                        fill={`rgb(${r},${g},${b})`}
                      />
                    );
                  })}
                </g>
              );
            })}
          </g>

          {/* Strike zone overlay */}
          <rect
            x={szX1} y={szZ1} width={szX2 - szX1} height={szZ2 - szZ1}
            fill="none" stroke={color} opacity={0.35}
            strokeWidth={1} strokeDasharray="4 3"
          />
          <line x1={(szX1 + szX2) / 2} y1={szZ1} x2={(szX1 + szX2) / 2} y2={szZ2}
                stroke={color} opacity={0.15} strokeWidth={0.75} />
          <line x1={szX1} y1={(szZ1 + szZ2) / 2} x2={szX2} y2={(szZ1 + szZ2) / 2}
                stroke={color} opacity={0.15} strokeWidth={0.75} />

          {([
            { label: 'UP',   x: WIDTH / 2, y: 11,         anchor: 'middle' },
            { label: 'DOWN', x: WIDTH / 2, y: HEIGHT - 4, anchor: 'middle' },
            { label: 'IN',   x: 4,         y: HEIGHT / 2, anchor: 'start'  },
            { label: 'AWAY', x: WIDTH - 4, y: HEIGHT / 2, anchor: 'end'    },
          ] as const).map(({ label, x, y, anchor }) => (
            <text key={label} x={x} y={y} textAnchor={anchor}
                  fontSize={9} fill="rgba(255,255,255,0.28)" fontFamily="var(--font-mono)">
              {label}
            </text>
          ))}
        </svg>

        {isLoading && (
          <div style={{
            position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
            color: 'var(--text-3)', fontSize: 11, fontFamily: 'var(--font-mono)',
          }}>
            Loading…
          </div>
        )}

        {!isLoading && !hasData && (
          <div style={{
            position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
            color: 'var(--text-3)', fontSize: 11, fontFamily: 'var(--font-mono)',
          }}>
            No Statcast data
          </div>
        )}
      </div>

      <div className="pitch-zone-legend">
        <span>Cold</span>
        <div className="pitch-zone-gradient" style={{
          background: `linear-gradient(to right, ${
            LAYERS.map((l, i) =>
              `rgb(${l.rgb.join(',')}) ${Math.round(i / (LAYERS.length - 1) * 100)}%`
            ).join(', ')
          })`,
        }} />
        <span>Hot</span>
      </div>
    </div>
  );
}
