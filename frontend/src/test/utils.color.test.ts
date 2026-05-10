import { describe, it, expect } from 'vitest';
import { playerColor, colorTint } from '../utils/color';

describe('playerColor', () => {
  it('returns an oklch color string', () => {
    expect(playerColor('ruthba01')).toMatch(/^oklch\(0\.72 0\.18 \d+(\.\d+)?\)$/);
  });

  it('is deterministic — same id always produces same color', () => {
    expect(playerColor('ruthba01')).toBe(playerColor('ruthba01'));
  });

  it('produces different colors for different ids', () => {
    expect(playerColor('ruthba01')).not.toBe(playerColor('gehrilo01'));
  });

  it('hue is within 0–359', () => {
    const match = playerColor('bondsba01').match(/oklch\(0\.72 0\.18 (\d+)/);
    const hue = Number(match?.[1]);
    expect(hue).toBeGreaterThanOrEqual(0);
    expect(hue).toBeLessThan(360);
  });

  it('handles single-character id without throwing', () => {
    expect(() => playerColor('a')).not.toThrow();
  });
});

describe('colorTint', () => {
  it('returns a color-mix string', () => {
    const result = colorTint('oklch(0.72 0.18 120)', 0.5);
    expect(result).toContain('color-mix(in oklch,');
    expect(result).toContain('50%');
    expect(result).toContain('transparent');
  });

  it('rounds alpha to nearest percent', () => {
    expect(colorTint('red', 0.333)).toContain('33%');
    expect(colorTint('red', 0.666)).toContain('67%');
  });

  it('clamps to 100% at alpha=1', () => {
    expect(colorTint('red', 1)).toContain('100%');
  });

  it('clamps to 0% at alpha=0', () => {
    expect(colorTint('red', 0)).toContain('0%');
  });
});
