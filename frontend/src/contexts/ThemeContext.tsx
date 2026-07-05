import React, { createContext, useContext, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  DEFAULT_THEME,
  getThemeByKey,
  isValidThemeKey,
  THEME_KEYS,
  THEME_STORAGE_KEY,
  Theme,
  ThemeKey,
} from "../lib/themes";

interface ThemeContextValue {
  themeKey: ThemeKey;
  theme: Theme;
  setThemeKey: (key: ThemeKey) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getStoredTheme(): ThemeKey {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored && isValidThemeKey(stored)) {
      return stored;
    }
  } catch {
    // ignore storage errors
  }
  return DEFAULT_THEME;
}

function applyThemeClass(key: ThemeKey) {
  const html = document.documentElement;
  const targetClass = `theme-${key}`;
  if (html.classList.contains(targetClass)) {
    for (const k of THEME_KEYS) {
      if (k !== key) html.classList.remove(`theme-${k}`);
    }
    return;
  }
  for (const k of THEME_KEYS) {
    html.classList.remove(`theme-${k}`);
  }
  html.classList.add(targetClass);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeKey, setThemeKeyState] = useState<ThemeKey>(getStoredTheme);
  const theme = useMemo(() => getThemeByKey(themeKey) ?? getThemeByKey(DEFAULT_THEME)!, [themeKey]);

  const setThemeKey = (key: ThemeKey) => {
    setThemeKeyState(key);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, key);
    } catch {
      // ignore storage errors
    }
  };

  useLayoutEffect(() => {
    applyThemeClass(themeKey);
  }, [themeKey]);

  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === THEME_STORAGE_KEY && e.newValue && isValidThemeKey(e.newValue)) {
        setThemeKeyState(e.newValue);
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const value = useMemo(
    () => ({ themeKey, theme, setThemeKey }),
    [themeKey, theme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
