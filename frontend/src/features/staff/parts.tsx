import { CircleAlert, ShieldAlert } from "lucide-react";
import { usePreferences } from "@/app/preferences";
import type { Texts } from "@/lib/i18n";
import type { Language, Priority } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { Reason } from "./types";

const PRIORITY_STYLE: Record<Priority, string> = {
  urgent: "bg-destructive text-white",
  high: "bg-warning/20 text-warning-foreground ring-1 ring-warning/50 dark:text-warning",
  medium: "bg-secondary text-secondary-foreground",
  low: "bg-muted text-muted-foreground",
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  const { t } = usePreferences();
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-md px-1.5 text-[0.7rem] font-semibold whitespace-nowrap",
        PRIORITY_STYLE[priority],
      )}
    >
      {t.priorities[priority]}
    </span>
  );
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

/** "5 dakika önce" / "5 minutes ago", written by the browser's own Intl rules for each language. */
export function timeAgo(iso: string, language: Language): string {
  const seconds = Math.round((Date.parse(iso) - Date.now()) / 1000);
  const format = new Intl.RelativeTimeFormat(language, { numeric: "auto" });
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return format.format(Math.round(seconds / size), unit);
  }
  return format.format(0, "minute");
}

export function reasonText(reason: Reason, t: Texts): string {
  const texts = t.staff.reasons;
  return reason.code === "weak_match"
    ? texts.weak_match(reason.score, reason.min)
    : texts[reason.code];
}

/** The decision's reasons: safety reasons (a human MUST answer) first and in red. */
export function ReasonList({ reasons }: { reasons: Reason[] }) {
  const { t } = usePreferences();
  const safety = new Set<Reason["code"]>(["escalation", "urgent"]);
  const sorted = [...reasons].sort(
    (a, b) => Number(safety.has(b.code)) - Number(safety.has(a.code)),
  );
  return (
    <ul className="space-y-2">
      {sorted.map((reason) => {
        const Icon = safety.has(reason.code) ? ShieldAlert : CircleAlert;
        return (
          <li key={reason.code} className="flex gap-2.5 text-sm">
            <Icon
              className={cn(
                "mt-0.5 size-4 shrink-0",
                safety.has(reason.code) ? "text-destructive" : "text-muted-foreground",
              )}
            />
            {reasonText(reason, t)}
          </li>
        );
      })}
    </ul>
  );
}
