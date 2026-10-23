import { useEffect, useState } from "react";
import { usePreferences } from "@/app/preferences";
import { cn } from "@/lib/utils";

const STAGE_MS = 1200;

/** While waiting: the PATH a request takes, with a highlight moving along it, and the real
 *  elapsed time. The server answers in one request, so this never claims a step is finished
 *  (an earlier version showed timed checkmarks; real progress would need streaming, SSE). */
export function Thinking() {
  const { t } = usePreferences();
  const [tick, setTick] = useState(0);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const stages = setInterval(() => setTick((n) => n + 1), STAGE_MS);
    const clock = setInterval(() => setSeconds((n) => n + 1), 1000);
    return () => {
      clearInterval(stages);
      clearInterval(clock);
    };
  }, []);

  const active = tick % t.steps.length;
  return (
    <div className="rounded-2xl border bg-card p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm font-medium" aria-live="polite">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-brand-text opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-brand-text" />
          </span>
          {t.working}
        </p>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {t.elapsed(seconds)}
        </span>
      </div>
      <ol className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        {t.steps.map((label, index) => (
          <li key={label} className="flex items-center gap-2">
            {index > 0 && (
              <span aria-hidden className="text-muted-foreground/50">
                →
              </span>
            )}
            <span
              className={cn(
                "transition-colors duration-500",
                index === active ? "text-foreground" : "text-muted-foreground/60",
              )}
            >
              {label}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
