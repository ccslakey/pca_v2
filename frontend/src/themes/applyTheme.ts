import type { Theme } from './types';

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  const c = theme.colors;
  const set = (k: string, v: string) => root.style.setProperty(k, v);

  set('--bg-0', c.bg0); set('--bg-1', c.bg1); set('--bg-2', c.bg2); set('--bg-3', c.bg3);
  set('--line', c.line); set('--line-soft', c.lineSoft);
  set('--text-0', c.text0); set('--text-1', c.text1); set('--text-2', c.text2); set('--text-3', c.text3);
  set('--accent', c.accent); set('--accent-2', c.accent2);
  set('--success', c.success); set('--danger', c.danger); set('--warning', c.warning);
  c.chart.forEach((color, i) => set(`--chart-${i + 1}`, color));
  set('--grid-dot', c.gridDot);
  set('--chart-grid-style', theme.chartGridStyle);

  set('--font-sans', theme.fonts.sans);
  set('--font-mono', theme.fonts.mono);
  set('--font-display', theme.fonts.display);

  set('--radius-sm', theme.radius.sm + 'px');
  set('--radius', theme.radius.md + 'px');
  set('--radius-lg', theme.radius.lg + 'px');

  set('--shadow-1', theme.shadow);

  root.setAttribute('data-theme-mode', theme.mode);
  root.setAttribute('data-theme-id', theme.id);
}
