import { ArrowUpRight, ShieldAlert } from "lucide-react";
import { usePreferences } from "@/app/preferences";
import { Composer } from "./composer";

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
    <div className="flex flex-wrap justify-center gap-2">
      {t.examples.map((question) => (
        <button
          key={question}
          type="button"
          onClick={() => onPick(question)}
          className="rounded-full border bg-card/60 px-3.5 py-1.5 text-sm text-muted-foreground transition-colors hover:border-ring/50 hover:text-foreground"
        >
          {question}
        </button>
      ))}
    </div>
  );
}

function HowItWorks() {
  const { t } = usePreferences();
  return (
    <section className="w-full">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {t.howTitle}
      </h2>
      <ol className="mt-4 grid gap-6 sm:grid-cols-3">
        {t.howSteps.map((step, index) => (
          <li key={step.title}>
            <span className="font-heading text-sm font-bold text-brand-text tabular-nums">
              {String(index + 1).padStart(2, "0")}
            </span>
            <p className="mt-1 text-sm font-semibold">{step.title}</p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function QuickLinks() {
  const { t } = usePreferences();
  return (
    <section className="w-full">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {t.quickLinks}
      </h2>
      <div className="mt-4 flex flex-wrap gap-2">
        {SYSTEMS.map((system) => (
          <a
            key={system.name}
            href={system.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-lg border bg-card/60 px-3 py-1.5 text-sm font-medium transition-colors hover:border-ring/50"
          >
            {system.name} <ArrowUpRight className="size-3.5 text-muted-foreground" />
          </a>
        ))}
      </div>
    </section>
  );
}

export function EmptyState({ onSend, busy }: { onSend: (text: string) => void; busy: boolean }) {
  const { t } = usePreferences();
  return (
    <div className="relative">
      {/* The soft red glow behind the welcome area (decoration only). */}
      <div
        aria-hidden
        className="hero-glow pointer-events-none absolute inset-x-0 top-0 h-[34rem]"
      />
      <div className="relative mx-auto flex max-w-2xl flex-col items-center pt-16 text-center sm:pt-24">
        <h1 className="bg-linear-to-b from-foreground to-foreground/65 bg-clip-text pb-1 font-heading text-3xl font-bold tracking-tight text-balance text-transparent sm:text-5xl">
          {t.welcomeTitle}
        </h1>
        <p className="mt-4 max-w-lg text-pretty text-muted-foreground">{t.welcomeText}</p>
        <div className="mt-8 w-full text-left">
          <Composer onSend={onSend} busy={busy} />
        </div>
        <p className="mt-3 flex items-start gap-1.5 text-left text-xs text-muted-foreground">
          <ShieldAlert className="mt-px size-3.5 shrink-0" /> {t.notice}
        </p>
        <div className="mt-8">
          <Examples onPick={onSend} />
        </div>
      </div>
      <div className="relative mx-auto mt-20 max-w-2xl space-y-12 border-t pt-10 pb-12">
        <HowItWorks />
        <QuickLinks />
        <p className="text-xs text-muted-foreground">{t.footer}</p>
      </div>
    </div>
  );
}
