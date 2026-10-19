import { describe, it, expect } from 'vitest';
import { initials } from '../utils/format';

describe('initials', () => {
  it('uses the first and last name', () => {
    expect(initials('Mike Trout')).toBe('MT');
    expect(initials('Tony La Russa')).toBe('TR');
  });

  it('skips generational suffixes', () => {
    expect(initials('Ken Griffey Jr.')).toBe('KG');
    expect(initials('Vladimir Guerrero Jr')).toBe('VG');
    expect(initials('Ken Griffey Sr.')).toBe('KG');
    expect(initials('Cal Ripken III')).toBe('CR');
    expect(initials('Jim Bunning IV')).toBe('JB');
  });

  it('falls back to the first two letters of a single name', () => {
    expect(initials('Ichiro')).toBe('IC');
  });
});
