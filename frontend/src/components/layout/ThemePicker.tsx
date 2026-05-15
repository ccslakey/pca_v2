import { useRef, useState, useEffect } from "react";
import { THEMES } from "../../themes/themes";
import { useTheme } from "../../themes/ThemeContext";
import type { Theme } from "../../themes/types";
import "./ThemePicker.scss";

function ThemeSwatches({ theme }: { theme: Theme }) {
  const strips = [
    theme.colors.bg1,
    theme.colors.bg2,
    theme.colors.accent,
    theme.colors.accent2,
    theme.colors.text0,
  ];
  return (
    <div className="tp-swatches">
      {strips.map((c, i) => (
        <div key={i} style={{ background: c }} />
      ))}
    </div>
  );
}

function ThemeOption({
  theme,
  active,
  onPick,
}: {
  theme: Theme;
  active: boolean;
  onPick: (t: Theme) => void;
}) {
  return (
    <div
      className={`tp-option${active ? " is-active" : ""}`}
      onClick={() => onPick(theme)}
      role="option"
      aria-selected={active}
    >
      <ThemeSwatches theme={theme} />
      <div className="tp-option-body">
        <div
          className="tp-option-name"
          style={{ fontFamily: theme.fonts.display }}
        >
          {theme.label}
        </div>
        <div className="tp-option-tagline">{theme.tagline.split(" · ")[0]}</div>
      </div>
      {active && (
        <svg
          className="tp-check"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      )}
    </div>
  );
}

export function ThemePicker() {
  const { themeId, theme, setThemeId } = useTheme();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node))
        setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const darkThemes = THEMES.filter((t) => t.mode === "dark");
  const lightThemes = THEMES.filter((t) => t.mode === "light");
  const triggerSwatches = [
    theme.colors.bg3,
    theme.colors.accent,
    theme.colors.text0,
  ];

  return (
    <div className="theme-picker" ref={wrapRef}>
      <button
        className="tp-trigger"
        onClick={() => setOpen((o) => !o)}
        title="Switch theme"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {/* not sure if we will include these */}
        <span className="tp-trigger-swatches" aria-hidden="true">
          {triggerSwatches.map((c, i) => (
            <span
              key={i}
              className="tp-trigger-swatch"
              style={{ background: c }}
            />
          ))}
        </span>
        <span className="tp-trigger-label">{theme.label}</span>
        <svg
          className="tp-caret"
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div className="tp-menu" role="listbox">
          <div className="tp-menu-section">
            <span className="tp-mode-dot" data-mode="dark" />
            Dark
          </div>
          {darkThemes.map((t) => (
            <ThemeOption
              key={t.id}
              theme={t}
              active={t.id === themeId}
              onPick={(t) => {
                setThemeId(t.id);
                setOpen(false);
              }}
            />
          ))}
          <div className="tp-menu-section">
            <span className="tp-mode-dot" data-mode="light" />
            Light
          </div>
          {lightThemes.map((t) => (
            <ThemeOption
              key={t.id}
              theme={t}
              active={t.id === themeId}
              onPick={(t) => {
                setThemeId(t.id);
                setOpen(false);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
