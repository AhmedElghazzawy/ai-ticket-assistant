import { ArrowUpRight, ShieldAlert } from "lucide-react";
import { usePreferences } from "@/app/preferences";
import { RESULTS } from "@/lib/showcase";
import { Composer } from "./composer";
import { LiveExample } from "./live-example";

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
      <h2 className="signal text-xs font-semibold uppercase tracking-widest text-muted-foreground">
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
      <h2 className="signal text-xs font-semibold uppercase tracking-widest text-muted-foreground">
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

function Results() {
  const { t } = usePreferences();
  const r = RESULTS;
  const rows = [
    { value: `${r.missedEscalations.missed}/${r.missedEscalations.of}`, label: t.results.missed },
    { value: `${r.rightDocumentTop3.hits}/${r.rightDocumentTop3.of}`, label: t.results.top3 },
    { value: `${r.unsafeAutoSends.unsafe}/${r.unsafeAutoSends.of}`, label: t.results.unsafe },
    { value: String(r.documents), label: t.results.documents },
  ];
  return (
    <section className="w-full text-left">
      <h2 className="signal text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {t.results.title}
      </h2>
      <dl className="mt-4 grid grid-cols-2 gap-3">
        {rows.map((row) => (
          <div key={row.label} className="rounded-xl border bg-card/60 p-4">
            <dt className="sr-only">{row.label}</dt>
            <dd className="font-mono text-3xl font-semibold tracking-tight">{row.value}</dd>
            <dd className="mt-1 text-xs leading-snug text-muted-foreground">{row.label}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{t.results.note}</p>
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
        className="hero-dots pointer-events-none absolute inset-x-0 top-0 h-[34rem]"
      />
      <div
        aria-hidden
        className="hero-glow pointer-events-none absolute inset-x-0 top-0 h-[34rem]"
      />
      <div className="relative mx-auto flex max-w-2xl flex-col items-center pt-12 text-center sm:pt-16">
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
        <div className="mt-6">
          <Examples onPick={onSend} />
        </div>
      </div>
      <div className="relative mx-auto mt-14 grid max-w-5xl items-start gap-8 lg:grid-cols-[1.35fr_1fr]">
        <LiveExample onAsk={onSend} />
        <Results />
      </div>
      <div className="relative mx-auto mt-16 max-w-5xl space-y-12 border-t pt-10 pb-12">
        <HowItWorks />
        <QuickLinks />
        <p className="text-xs text-muted-foreground">{t.footer}</p>
      </div>
    </div>
  );
}
