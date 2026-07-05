import React, { useEffect, useRef, useState } from "react";
import { Check, Palette } from "lucide-react";
import { useTheme } from "../contexts/ThemeContext";
import { THEMES, ThemeKey } from "../lib/themes";

export function ThemeSelector() {
  const { themeKey, setThemeKey } = useTheme();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const activeTheme = THEMES.find((t) => t.key === themeKey)!;

  const handleSelect = (key: ThemeKey) => {
    setThemeKey(key);
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }

    const currentIndex = THEMES.findIndex((t) => t.key === themeKey);
    if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % THEMES.length;
      setThemeKey(THEMES[nextIndex].key);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prevIndex = (currentIndex - 1 + THEMES.length) % THEMES.length;
      setThemeKey(THEMES[prevIndex].key);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setOpen(false);
    }
  };

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="w-full flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-theme-muted transition-all hover:bg-accent-blue/[0.06] hover:text-accent-blue"
      >
        <Palette className="w-4 h-4" />
        <span className="flex-1 text-left">{activeTheme.name}</span>
      </button>

      {open && (
        <div
          className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-fintech-border bg-surface-elevated/95 backdrop-blur-xl shadow-xl p-2 z-50"
          role="listbox"
          aria-label="Chọn giao diện"
        >
          {THEMES.map((theme) => (
            <button
              key={theme.key}
              role="option"
              aria-selected={theme.key === themeKey}
              onClick={() => handleSelect(theme.key)}
              className={`w-full flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${theme.key === themeKey
                  ? "bg-accent-blue/10 text-accent-blue"
                  : "text-theme-muted hover:bg-surface-card"
                }`}
            >
              <span className="flex gap-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: theme.chartColors[0] }}
                />
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: theme.chartColors[1] }}
                />
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: theme.chartColors[2] }}
                />
              </span>
              <span className="flex-1">{theme.name}</span>
              {theme.key === themeKey && <Check className="w-4 h-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
