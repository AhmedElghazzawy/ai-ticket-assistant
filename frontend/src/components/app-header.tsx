import { Monitor, Moon, SquarePen, Sun } from "lucide-react";
import { type Theme, usePreferences } from "@/app/preferences";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Language } from "@/lib/types";
import { cn } from "@/lib/utils";

const THEME_ICONS = { light: Sun, dark: Moon, system: Monitor } satisfies Record<Theme, unknown>;

/** BŞEÜ mark: a navy tile with the initials (the official logo can replace it). */
export function BrandMark() {
  return (
    <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary font-heading text-[0.62rem] font-bold tracking-tight text-primary-foreground">
      BŞEÜ
    </div>
  );
}

export function LanguageSwitch() {
  const { language, setLanguage } = usePreferences();
  return (
    <fieldset className="flex rounded-lg border bg-muted/50 p-0.5 text-xs font-semibold">
      <legend className="sr-only">Dil / Language</legend>
      {(["tr", "en"] as const satisfies Language[]).map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={language === option}
          onClick={() => setLanguage(option)}
          className={cn(
            "rounded-md px-2.5 py-1 uppercase transition-colors",
            language === option
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option}
        </button>
      ))}
    </fieldset>
  );
}

export function ThemeMenu() {
  const { theme, setTheme, t } = usePreferences();
  const Icon = THEME_ICONS[theme];
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={<Button variant="ghost" size="icon" aria-label={t.theme[theme]} />}
      >
        <Icon />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup value={theme} onValueChange={(value) => setTheme(value as Theme)}>
          {(Object.keys(THEME_ICONS) as Theme[]).map((option) => {
            const OptionIcon = THEME_ICONS[option];
            return (
              <DropdownMenuRadioItem key={option} value={option}>
                <OptionIcon /> {t.theme[option]}
              </DropdownMenuRadioItem>
            );
          })}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppHeader({ onNewChat }: { onNewChat: () => void }) {
  const { t } = usePreferences();
  return (
    <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-5xl items-center gap-3 px-4">
        <BrandMark />
        <div className="min-w-0 leading-tight">
          <p className="truncate font-heading text-sm font-bold">{t.title}</p>
          <p className="truncate text-xs text-muted-foreground">{t.university}</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <Button variant="outline" size="sm" onClick={onNewChat} className="hidden sm:flex">
            <SquarePen /> {t.newChat}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onNewChat}
            aria-label={t.newChat}
            className="sm:hidden"
          >
            <SquarePen />
          </Button>
          <LanguageSwitch />
          <ThemeMenu />
        </div>
      </div>
    </header>
  );
}
