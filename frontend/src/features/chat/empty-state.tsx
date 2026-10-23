import {
  ArrowUpRight,
  BookOpenCheck,
  CalendarDays,
  CreditCard,
  FileSearch,
  GraduationCap,
  KeyRound,
  MessageSquareText,
  Route,
} from "lucide-react";
import { usePreferences } from "@/app/preferences";

const ICONS = [GraduationCap, CreditCard, CalendarDays, KeyRound]; // same order as t.examples
const STEP_ICONS = [MessageSquareText, FileSearch, Route]; // same order as t.howSteps

// Official addresses, the same ones our knowledge-base documents cite (bilisim_hesaplar).
const SYSTEMS = [
  { name: "OBS", url: "https://obs.bilecik.edu.tr/" },
  { name: "SOFRA", url: "https://sofra.bilecik.edu.tr/" },
  { name: "UZEM", url: "https://ders.bilecik.edu.tr/" },
  { name: "e-Devlet", url: "https://www.turkiye.gov.tr/" },
];

function Examples({ onPick }: { onPick: (question: string) => void }) {
  const { t } = usePreferences();
  return (
    <div className="mt-8 grid w-full max-w-2xl gap-2.5 sm:grid-cols-2">
      {t.examples.map((question, index) => {
        const Icon = ICONS[index] ?? GraduationCap;
        return (
          <button
            key={question}
            type="button"
            onClick={() => onPick(question)}
            className="group flex items-center gap-3 rounded-xl border bg-card p-3.5 text-left text-sm shadow-xs transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
          >
            <Icon className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
            {question}
          </button>
        );
      })}
    </div>
  );
}

function HowItWorks() {
  const { t } = usePreferences();
  return (
    <section className="mt-12 w-full max-w-2xl text-left">
      <h2 className="font-heading text-sm font-bold">{t.howTitle}</h2>
      <ol className="mt-3 grid gap-3 sm:grid-cols-3">
        {t.howSteps.map((step, index) => {
          const Icon = STEP_ICONS[index] ?? Route;
          return (
            <li key={step.title} className="rounded-xl border bg-card p-3.5">
              <span className="flex items-center gap-2 text-sm font-semibold">
                <span className="flex size-7 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <Icon className="size-4" />
                </span>
                {step.title}
              </span>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{step.text}</p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function QuickLinks() {
  const { t } = usePreferences();
  return (
    <section className="mt-8 w-full max-w-2xl text-left">
      <h2 className="font-heading text-sm font-bold">{t.quickLinks}</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {SYSTEMS.map((system) => (
          <a
            key={system.name}
            href={system.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-lg border bg-card px-3 py-2 text-sm font-medium transition-colors hover:border-primary/40 hover:text-primary"
          >
            {system.name} <ArrowUpRight className="size-3.5 text-muted-foreground" />
          </a>
        ))}
      </div>
    </section>
  );
}

export function EmptyState({ onPick }: { onPick: (question: string) => void }) {
  const { t } = usePreferences();
  return (
    <div className="flex flex-col items-center py-10 text-center sm:py-14">
      <span className="mb-5 flex size-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
        <BookOpenCheck className="size-6" />
      </span>
      <h1 className="font-heading text-2xl font-bold tracking-tight text-balance sm:text-3xl">
        {t.welcomeTitle}
      </h1>
      <p className="mt-3 max-w-lg text-pretty text-muted-foreground">{t.welcomeText}</p>
      <Examples onPick={onPick} />
      <HowItWorks />
      <QuickLinks />
      <p className="mt-12 max-w-2xl text-xs text-muted-foreground">{t.footer}</p>
    </div>
  );
}
