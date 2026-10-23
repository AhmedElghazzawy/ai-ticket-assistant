import { Check, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { usePreferences } from "@/app/preferences";
import { cn } from "@/lib/utils";

const STEP_MS = 800;

/** The pipeline's stages while waiting. Timed for now; real progress comes with streaming (SSE). */
export function Thinking() {
  const { t } = usePreferences();
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(
      () => setStep((current) => Math.min(current + 1, t.steps.length - 1)),
      STEP_MS,
    );
    return () => clearInterval(timer);
  }, [t.steps.length]);

  return (
    <div className="rounded-2xl border bg-card p-4 shadow-sm sm:p-5" aria-live="polite">
      <ol className="space-y-2.5">
        {t.steps.map((label, index) => (
          <li
            key={label}
            className={cn(
              "flex items-center gap-2.5 text-sm transition-colors",
              index > step ? "text-muted-foreground/50" : "text-foreground",
            )}
          >
            {index < step ? (
              <Check className="size-4 text-success" />
            ) : index === step ? (
              <LoaderCircle className="size-4 animate-spin text-brand-text" />
            ) : (
              <span className="size-4 rounded-full border" />
            )}
            {label}
          </li>
        ))}
      </ol>
    </div>
  );
}
