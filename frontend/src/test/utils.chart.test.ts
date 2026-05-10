import { describe, it, expect } from 'vitest';
import { fmtMetric, peakSeason, careerWar, yDomain, xTicks } from '../utils/chart';
import type { ChartSeason } from '../types';

function season(year: number, vals: Partial<ChartSeason> = {}): ChartSeason {
  return { season: year, age: null, war: null, hr: null, avg: null, ops: null, era: null, so: null, ...vals };
}

describe('fmtMetric', () => {
  it('returns em-dash for null', () => {
    expect(fmtMetric('war', null)).toBe('—');
  });

  it('formats war to 1 decimal', () => {
    expect(fmtMetric('war', 7.25)).toBe('7.3');
    expect(fmtMetric('war', 0)).toBe('0.0');
  });

  it('formats avg with leading dot', () => {
    expect(fmtMetric('avg', 0.312)).toBe('.312');
    expect(fmtMetric('avg', 1.000)).toBe('1.000');
  });

  it('formats ops with leading dot', () => {
    expect(fmtMetric('ops', 0.845)).toBe('.845');
  });

  it('formats era to 2 decimals', () => {
    expect(fmtMetric('era', 3.5)).toBe('3.50');
  });

  it('rounds hr and so to integers', () => {
    expect(fmtMetric('hr', 47.6)).toBe('48');
    expect(fmtMetric('so', 200)).toBe('200');
  });

  it('returns em-dash for NaN', () => {
    expect(fmtMetric('war', NaN)).toBe('—');
  });
});

describe('peakSeason', () => {
  const seasons = [
    season(2000, { war: 5.0 }),
    season(2001, { war: 9.2 }),
    season(2002, { war: 3.1 }),
  ];

  it('returns the season with highest value', () => {
    const pk = peakSeason(seasons, 'war');
    expect(pk).toEqual({ season: 2001, val: 9.2 });
  });

  it('returns lowest value for ERA (lower is better)', () => {
    const pitching = [
      season(2000, { era: 4.5 }),
      season(2001, { era: 2.1 }),
      season(2002, { era: 3.8 }),
    ];
    const pk = peakSeason(pitching, 'era');
    expect(pk).toEqual({ season: 2001, val: 2.1 });
  });

  it('returns null when no seasons have data', () => {
    expect(peakSeason([season(2000), season(2001)], 'hr')).toBeNull();
  });

  it('returns null for empty array', () => {
    expect(peakSeason([], 'war')).toBeNull();
  });

  it('ignores null values', () => {
    const mixed = [season(2000, { hr: null }), season(2001, { hr: 45 })];
    const pk = peakSeason(mixed, 'hr');
    expect(pk?.season).toBe(2001);
  });
});

describe('careerWar', () => {
  it('sums war across seasons', () => {
    expect(careerWar([{ war: 5.0 }, { war: 3.2 }, { war: 7.1 }])).toBe(15.3);
  });

  it('treats null war as 0', () => {
    expect(careerWar([{ war: 5.0 }, { war: null }])).toBe(5.0);
  });

  it('returns 0 for empty array', () => {
    expect(careerWar([])).toBe(0);
  });

  it('rounds to one decimal', () => {
    expect(careerWar([{ war: 1.05 }, { war: 1.05 }])).toBe(2.1);
  });
});

describe('yDomain', () => {
  it('returns [0, 10] for empty input', () => {
    expect(yDomain([], 'war')).toEqual([0, 10]);
  });

  it('includes 0 as floor for WAR', () => {
    const [lo] = yDomain([2, 8], 'war');
    expect(lo).toBe(0);
  });

  it('adds padding above max for WAR', () => {
    const [, hi] = yDomain([0, 8], 'war');
    expect(hi).toBeGreaterThan(8);
  });

  it('floors ERA at 0 when min is already low', () => {
    const [lo] = yDomain([0.1, 4.0], 'era');
    expect(lo).toBeGreaterThanOrEqual(0);
  });

  it('adds small padding to AVG', () => {
    const [lo, hi] = yDomain([0.250, 0.330], 'avg');
    expect(lo).toBeLessThan(0.250);
    expect(hi).toBeGreaterThan(0.330);
  });
});

describe('xTicks', () => {
  it('returns a tick for each year in a short range', () => {
    const ticks = xTicks(2000, 2005);
    expect(ticks).toEqual([2000, 2001, 2002, 2003, 2004, 2005]);
  });

  it('uses step of 2 for medium ranges', () => {
    const ticks = xTicks(2000, 2012);
    expect(ticks.every((_v, i) => i === 0 || ticks[i] - ticks[i - 1] === 2)).toBe(true);
  });

  it('uses step of 4 for long ranges', () => {
    const ticks = xTicks(1980, 2024);
    expect(ticks.every((_v, i) => i === 0 || ticks[i] - ticks[i - 1] === 4)).toBe(true);
  });
});
