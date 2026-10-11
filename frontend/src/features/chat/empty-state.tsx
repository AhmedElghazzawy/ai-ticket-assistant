import { BookOpenCheck, CalendarDays, CreditCard, GraduationCap, KeyRound } from "lucide-react";
import { usePreferences } from "@/app/preferences";

const ICONS = [GraduationCap, CreditCard, CalendarDays, KeyRound]; // same order as t.examples

export function EmptyState({ onPick }: { onPick: (question: string) => void }) {
  const { t } = usePreferences();
  return (
    <div className="flex flex-col items-center py-10 text-center sm:py-16">
      <span className="mb-5 flex size-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
        <BookOpenCheck className="size-6" />
      </span>
      <h1 className="font-heading text-2xl font-bold tracking-tight text-balance sm:text-3xl">
        {t.welcomeTitle}
      </h1>
      <p className="mt-3 max-w-lg text-pretty text-muted-foreground">{t.welcomeText}</p>
      <div className="mt-8 grid w-full max-w-2xl gap-2.5 sm:grid-cols-2">
        {t.examples.map((question, index) => {
          const Icon = ICONS[index] ?? GraduationCap;
          return (
            <button
              key={question}
              type="button"
              onClick={() => onPick(question)}
              className="group flex items-center gap-3 rounded-xl border bg-card p-3.5 text-left text-sm shadow-xs transition-all hover:-translate-y-0.5 hover:border-ring/40 hover:shadow-md"
            >
              <Icon className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-accent-foreground" />
              {question}
            </button>
          );
        })}
      </div>
    </div>
  );
}
