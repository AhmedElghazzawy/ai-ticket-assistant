// "Nasıl karar verildi?": the real checks behind an answer, step by step. Built only from what
// the API sends for students (reason codes and the match score), never from the draft.
import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { usePreferences } from "@/app/preferences";
import type { TicketOut } from "@/lib/types";
import { cn } from "@/lib/utils";

type State = "ok" | "human" | "safety";

interface Step {
  state: State;
  lines: string[];
}

const DOT: Record<State, string> = {
  ok: "bg-success",
  human: "bg-warning",
  safety: "bg-destructive",
};

function buildSteps(result: TicketOut, t: ReturnType<typeof usePreferences>["t"]): Step[] {
  const codes = new Set(result.reasons.map((reason) => reason.code));
  const tr = t.trace;
  const classify: string[] = [
    `${t.categories[result.category]} · ${t.priorities[result.priority]}`,
  ];
  classify.push(codes.has("escalation") ? tr.needsHuman : tr.noHuman);
  if (codes.has("urgent")) classify.push(tr.urgent);
  if (codes.has("category_other")) classify.push(tr.other);
  return [
    {
      state:
        codes.has("escalation") || codes.has("urgent")
          ? "safety"
          : codes.has("category_other")
            ? "human"
            : "ok",
      lines: classify,
    },
    {
      state: codes.has("weak_match") ? "human" : "ok",
      lines: [
        codes.has("weak_match")
          ? tr.weak(result.top_score, result.min_score)
          : tr.match(result.top_score, result.min_score),
      ],
    },
    {
      state:
        codes.has("not_covered") || codes.has("no_citation") || codes.has("ungrounded")
          ? "human"
          : "ok",
      lines: [
        codes.has("not_covered") ? tr.notCovered : tr.covered,
        codes.has("no_citation") ? tr.notCited : codes.has("ungrounded") ? tr.notQuoted : tr.cited,
      ],
    },
    {
      state: result.auto_send ? "ok" : "human",
      lines: [result.auto_send ? tr.sent : result.first_help ? tr.firstHelp : tr.forwarded],
    },
  ];
}

export function DecisionTrace({ result }: { result: TicketOut }) {
  const { t } = usePreferences();
  const [open, setOpen] = useState(false);
  const steps = buildSteps(result, t);

  return (
    <div className="rounded-lg border bg-background/40">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground"
      >
        <span className="flex items-center gap-2">
          {/* a tiny preview of the four checks, visible even when closed */}
          <span className="flex gap-1" aria-hidden>
            {steps.map((step, index) => (
              <span
                key={t.trace.steps[index]}
                className={cn("size-1.5 rounded-full", DOT[step.state])}
              />
            ))}
          </span>
          {t.trace.title}
        </span>
        <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <ol className="relative mx-3.5 mb-3.5 space-y-4 border-l border-dashed pl-5">
          {steps.map((step, index) => (
            <li key={t.trace.steps[index]} className="relative">
              <span
                aria-hidden
                className={cn(
                  "absolute top-1 -left-[1.6rem] size-2.5 rounded-full ring-4 ring-card",
                  DOT[step.state],
                )}
              />
              <p className="flex items-baseline gap-2 text-sm font-semibold">
                <span className="font-mono text-xs text-muted-foreground">
                  {String(index + 1).padStart(2, "0")}
                </span>
                {t.trace.steps[index]}
              </p>
              {step.lines.map((line) => (
                <p key={line} className="mt-0.5 text-sm text-muted-foreground">
                  {line}
                </p>
              ))}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
