// The start page's live example: a REAL test question travels through the four checks with its
// real scores, then its real answer and source appear. It loops, so visitors see how the system
// thinks before they type. Motion stops for people who ask their computer for reduced motion.
import { FileText, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { usePreferences } from "@/app/preferences";
import { Button } from "@/components/ui/button";
import { EXAMPLES } from "@/lib/showcase";
import { cn } from "@/lib/utils";

const STEP_MS = 1100;
const HOLD_STEPS = 5; // the finished answer stays this many steps before the loop restarts
const LAST = 4; // 0: question only, 1-4: the checks (4 also shows the answer)

function useLoop(): number {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setPhase(LAST); // no animation: show the finished example
      return;
    }
    const timer = setInterval(() => setPhase((n) => (n + 1) % (LAST + 1 + HOLD_STEPS)), STEP_MS);
    return () => clearInterval(timer);
  }, []);
  return Math.min(phase, LAST);
}

export function LiveExample({ onAsk }: { onAsk: (question: string) => void }) {
  const { t, language } = usePreferences();
  const example = EXAMPLES[language];
  const phase = useLoop();
  const steps = [
    [`${t.categories[example.category]} · ${t.priorities[example.priority]}`, t.trace.noHuman],
    [t.trace.match(example.topScore, example.minScore)],
    [t.trace.covered, t.trace.cited],
    [t.trace.sent],
  ];

  return (
    <section className="w-full rounded-2xl border bg-card/70 p-4 text-left backdrop-blur-sm sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-60 motion-reduce:animate-none" />
            <span className="relative inline-flex size-2 rounded-full bg-success" />
          </span>
          {t.showcase.label}
        </p>
        <Button variant="ghost" size="sm" onClick={() => onAsk(example.question)}>
          <Play /> {t.showcase.ask}
        </Button>
      </div>
      <p className="mt-3 rounded-xl border bg-secondary px-3.5 py-2.5 text-sm">
        {example.question}
      </p>
      <ol className="mt-4 ml-1 space-y-3 border-l border-dashed pl-5" aria-label={t.trace.title}>
        {steps.map((lines, index) => {
          const reached = phase > index;
          return (
            <li
              key={t.trace.steps[index]}
              className={cn(
                "relative transition-opacity duration-500",
                reached ? "opacity-100" : "opacity-25",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "absolute top-1 -left-[1.6rem] size-2.5 rounded-full ring-4 ring-card transition-colors duration-500",
                  reached ? "bg-success" : "bg-muted-foreground/40",
                )}
              />
              <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
                <span className="font-mono text-xs text-muted-foreground">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="font-semibold">{t.trace.steps[index]}</span>
                <span className="text-muted-foreground">{lines.join(" ")}</span>
              </p>
            </li>
          );
        })}
      </ol>
      <div
        className={cn(
          "mt-4 rounded-xl border bg-background/60 p-3.5 transition-all duration-700",
          phase >= LAST ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
        )}
        aria-hidden={phase < LAST}
      >
        <p className="text-xs font-semibold text-success">{t.showcase.answer}</p>
        <p className="mt-1.5 text-sm leading-relaxed">{example.reply}</p>
        <p className="mt-2.5 flex items-center gap-1.5 text-xs text-muted-foreground">
          <FileText className="size-3.5 text-brand-text" />
          <span className="shrink-0 font-medium whitespace-nowrap text-foreground">
            {example.sourceSection}
          </span>
          <span className="truncate">· {example.sourceTitle}</span>
        </p>
      </div>
    </section>
  );
}
