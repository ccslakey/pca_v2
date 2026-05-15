import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { THEMES, DEFAULT_DARK_THEME_ID, DEFAULT_LIGHT_THEME_ID } from './themes';
import { applyTheme } from './applyTheme';
import type { Theme } from './types';

const STORAGE_KEY = 'pca-theme-id';

function getInitialThemeId(): string {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && THEMES.find(t => t.id === stored)) return stored;
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  return prefersDark ? DEFAULT_DARK_THEME_ID : DEFAULT_LIGHT_THEME_ID;
}

interface ThemeContextValue {
  themeId: string;
  theme: Theme;
  setThemeId: (id: string) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeId, setThemeIdState] = useState<string>(getInitialThemeId);

  const theme = THEMES.find(t => t.id === themeId) ?? THEMES[0];

  function setThemeId(id: string) {
    setThemeIdState(id);
    localStorage.setItem(STORAGE_KEY, id);
  }

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ themeId, theme, setThemeId }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
