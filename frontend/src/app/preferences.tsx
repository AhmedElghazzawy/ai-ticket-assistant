// Language and theme for the whole page, remembered in the browser between visits.

import { createContext, type ReactNode, use, useEffect, useState } from "react";
import { TEXTS, type Texts } from "@/lib/i18n";
import type { Language } from "@/lib/types";

export type Theme = "light" | "dark" | "system";

interface Preferences {
  language: Language;
  setLanguage: (language: Language) => void;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  t: Texts; // the texts in the chosen language
}

const PreferencesContext = createContext<Preferences | null>(null);

/** Reads a saved value; storage can be blocked (private mode), so failures fall back. */
function load<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const value = localStorage.getItem(key);
    return allowed.find((option) => option === value) ?? fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // not saved: the choice still works until the page is closed
  }
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState(() => load("language", ["tr", "en"] as const, "tr"));
  const [theme, setTheme] = useState(
    () => load("theme", ["light", "dark", "system"] as const, "dark"), // dark by default; a saved choice wins
  );

  useEffect(() => {
    save("language", language);
    document.documentElement.lang = language; // screen readers pronounce Turkish correctly
  }, [language]);

  useEffect(() => {
    save("theme", theme);
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && media.matches);
      document.documentElement.classList.toggle("dark", dark);
    };
    apply();
    media.addEventListener("change", apply); // follow the computer when it switches to dark mode
    return () => media.removeEventListener("change", apply);
  }, [theme]);

  return (
    <PreferencesContext value={{ language, setLanguage, theme, setTheme, t: TEXTS[language] }}>
      {children}
    </PreferencesContext>
  );
}

export function usePreferences(): Preferences {
  const preferences = use(PreferencesContext);
  if (!preferences) throw new Error("usePreferences must be used inside PreferencesProvider");
  return preferences;
}
