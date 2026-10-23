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

/** BŞEÜ mark: the initials on a tile, NOT the official logo (that needs the university's OK;
 *  docs/changelog.md, Stage 1). `onBrand`: white tile for the red header band. */
export function BrandMark({ onBrand = false }: { onBrand?: boolean }) {
  return (
    <div
      className={cn(
        "flex size-10 shrink-0 items-center justify-center rounded-xl font-heading text-[0.62rem] font-bold tracking-tight",
        onBrand ? "bg-brand-foreground text-brand" : "bg-primary text-primary-foreground",
      )}
    >
      BŞEÜ
    </div>
  );
}

/** Always visible: this is not an official university service, and no personal data please. */
export function NoticeBar() {
  const { t } = usePreferences();
  return <p className="bg-gold/15 px-4 py-1.5 text-center text-xs text-foreground">{t.notice}</p>;
}

export function LanguageSwitch({ onBrand = false }: { onBrand?: boolean }) {
  const { language, setLanguage } = usePreferences();
  return (
    <fieldset
      className={cn(
        "flex rounded-lg border p-0.5 text-xs font-semibold",
        onBrand ? "border-white/25 bg-white/10" : "bg-muted/50",
      )}
    >
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
              : onBrand
                ? "text-brand-foreground/85 hover:text-brand-foreground"
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
    <header className="sticky top-0 z-10">
      <NoticeBar />
      <div className="bg-brand text-brand-foreground">
        <div className="mx-auto flex h-16 max-w-5xl items-center gap-3 px-4">
          <BrandMark onBrand />
          <div className="min-w-0 leading-tight">
            <p className="font-heading text-sm font-bold">{t.title}</p>
            {/* Phones: the BŞEÜ tile already names the university, so the title gets the room. */}
            <p className="hidden truncate text-xs text-brand-foreground/80 sm:block">
              {t.university}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={onNewChat}
              className="hidden hover:bg-white/15 sm:flex"
            >
              <SquarePen /> {t.newChat}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onNewChat}
              aria-label={t.newChat}
              className="hover:bg-white/15 sm:hidden"
            >
              <SquarePen />
            </Button>
            <LanguageSwitch onBrand />
            <ThemeMenu />
          </div>
        </div>
      </div>
      {/* The official bilecik.edu.tr gradient, as a thin accent line (decoration only). */}
      <div className="h-1" style={{ background: "var(--brand-gradient)" }} />
    </header>
  );
}
