import { Link } from "@tanstack/react-router";
import { Inbox, Monitor, Moon, SquarePen, Sun } from "lucide-react";
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

/** BŞEÜ mark: the initials on a red tile, NOT the official logo (that needs the university's OK;
 *  docs/changelog.md, Stage 1). */
export function BrandMark() {
  return (
    <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary font-heading text-[0.58rem] font-bold tracking-tight text-primary-foreground glow-soft">
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
    <header className="sticky top-0 z-10 border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4">
        <BrandMark />
        <div className="min-w-0 leading-tight">
          <p className="font-heading text-sm font-bold">{t.title}</p>
          {/* Phones: the BŞEÜ tile already names the university, so the title gets the room. */}
          <p className="hidden truncate text-xs text-muted-foreground sm:block">{t.university}</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="icon"
            render={<Link to="/my-tickets" />}
            aria-label={t.myTickets}
            className="sm:hidden"
          >
            <Inbox />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            render={<Link to="/my-tickets" />}
            className="hidden sm:flex"
          >
            <Inbox /> {t.myTickets}
          </Button>
          <Button variant="ghost" size="sm" onClick={onNewChat} className="hidden sm:flex">
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
