import {
  ArrowUpRight,
  BadgeCheck,
  Building2,
  Clock,
  FileText,
  Forward,
  Lightbulb,
  Phone,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { useState } from "react";
import { usePreferences } from "@/app/preferences";
import { giveFeedback } from "@/client";
import { Button } from "@/components/ui/button";
import type { StoredSource, TicketOut } from "@/lib/types";
import { cn } from "@/lib/utils";
import { DecisionTrace } from "./decision-trace";

/** Thumbs up / down, saved with the ticket's secret code (the last choice counts). */
function FeedbackButtons({ result }: { result: TicketOut }) {
  const { t } = usePreferences();
  const [choice, setChoice] = useState<boolean | null>(null);

  async function send(helpful: boolean) {
    setChoice(helpful); // show it at once; a failed save is not worth an error for the student
    await giveFeedback({
      path: { ticket_id: result.ticket_id },
      body: { code: result.access_code, helpful },
    });
  }

  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground">
      <span className="mr-1">{choice === null ? t.helpful : t.thanks}</span>
      {([true, false] as const).map((helpful) => {
        const Icon = helpful ? ThumbsUp : ThumbsDown;
        return (
          <Button
            key={String(helpful)}
            variant="ghost"
            size="icon-sm"
            aria-label={helpful ? t.feedbackYes : t.feedbackNo}
            aria-pressed={choice === helpful}
            onClick={() => send(helpful)}
            className={cn(choice === helpful && "bg-accent text-accent-foreground")}
          >
            <Icon />
          </Button>
        );
      })}
    </div>
  );
}

function SourceCard({ source }: { source: StoredSource }) {
  const body = (
    <>
      <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
        <FileText className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{source.section}</span>
        <span className="block truncate text-xs text-muted-foreground">{source.title}</span>
        {/* The official source line; makes "Resmî olmayan kaynak" visible to the student. */}
        {source.source && (
          <span className="block truncate text-xs text-muted-foreground" title={source.source}>
            {source.source}
          </span>
        )}
      </span>
      {source.url && <ArrowUpRight className="size-4 shrink-0 text-muted-foreground" />}
    </>
  );
  const style =
    "flex min-w-0 items-center gap-3 rounded-lg border bg-background p-2.5 transition-colors";
  return source.url ? (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className={`${style} hover:border-ring/40 hover:bg-accent/40`}
    >
      {body}
    </a>
  ) : (
    <div className={style}>{body}</div>
  );
}

function SourceList({ sources }: { sources: StoredSource[] }) {
  const { t } = usePreferences();
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t.sources}
      </p>
      <div className={sources.length > 1 ? "grid gap-2 sm:grid-cols-2" : "grid gap-2"}>
        {sources.map((source) => (
          <SourceCard key={source.id} source={source} />
        ))}
      </div>
    </div>
  );
}

function TicketMeta({ result }: { result: TicketOut }) {
  const { t } = usePreferences();
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
      <span className="font-semibold text-foreground">
        {t.ticketNo} <span className="font-mono">#{result.ticket_id}</span>
      </span>
      <span aria-hidden>·</span>
      <span>{t.categories[result.category]}</span>
    </div>
  );
}

function EmergencyBanner() {
  const { t } = usePreferences();
  return (
    <a
      href="tel:112"
      className="flex items-center gap-3 rounded-lg bg-destructive px-4 py-3 text-sm font-semibold text-destructive-foreground"
    >
      <Phone className="size-4" /> {t.emergency}
    </a>
  );
}

/** Advice for what the rules do not answer. The PAGE labels it as not official, never the model. */
function GeneralHelp({ text }: { text: string }) {
  const { t } = usePreferences();
  return (
    <div className="space-y-2 rounded-lg border border-dashed bg-muted/40 p-3.5">
      <p className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
        <Lightbulb className="size-4" /> {t.generalHelp}
      </p>
      <p className="text-[0.95rem] leading-relaxed">{text}</p>
      <p className="text-xs text-muted-foreground">{t.generalHelpNote}</p>
    </div>
  );
}

function AnsweredCard({ result }: { result: TicketOut }) {
  const { t } = usePreferences();
  return (
    <div className="space-y-4">
      <p className="flex items-center gap-1.5 text-xs font-semibold text-success">
        <BadgeCheck className="size-4" /> {t.answered}
      </p>
      <p className="text-[0.95rem] leading-relaxed">{result.reply}</p>
      <SourceList sources={result.sources} />
      {result.general_help && <GeneralHelp text={result.general_help} />}
      <DecisionTrace result={result} />
      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <TicketMeta result={result} />
        <FeedbackButtons result={result} />
      </div>
    </div>
  );
}

function ForwardedCard({ result }: { result: TicketOut }) {
  const { t } = usePreferences();
  const official = result.first_help ? result.reply : null; // passed decision.show_first_help
  const answered = Boolean(official || result.general_help);
  return (
    <div className="space-y-4">
      {official && (
        <div className="space-y-3">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-success">
            <BadgeCheck className="size-4" /> {t.firstHelp}
          </p>
          <p className="text-[0.95rem] leading-relaxed">{official}</p>
          <SourceList sources={result.sources} />
        </div>
      )}
      {result.general_help && <GeneralHelp text={result.general_help} />}
      {answered ? (
        <div className="flex justify-end">
          <FeedbackButtons result={result} />
        </div>
      ) : (
        <>
          <p className="flex items-center gap-1.5 text-xs font-semibold text-warning-foreground dark:text-warning">
            <Forward className="size-4" /> {t.forwarded}
          </p>
          <p className="text-[0.95rem] leading-relaxed">{t.forwardedText}</p>
        </>
      )}
      <div className="space-y-3 rounded-lg border bg-muted/40 p-3.5">
        {answered && (
          <p className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <Forward className="size-4" /> {t.alsoForwarded}
          </p>
        )}
        <div className="flex items-start gap-3">
          <Building2 className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <div>
            <p className="text-xs text-muted-foreground">{t.office}</p>
            <p className="text-sm font-semibold">{t.offices[result.office]}</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <Clock className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <p className="text-sm">{t.nextStep}</p>
        </div>
      </div>
      <DecisionTrace result={result} />
      <div className="border-t pt-3">
        <TicketMeta result={result} />
      </div>
    </div>
  );
}

export function AnswerCard({ result }: { result: TicketOut }) {
  return (
    <div className="space-y-3">
      {result.emergency && <EmergencyBanner />}
      <div className="rounded-2xl border bg-card p-4 shadow-sm sm:p-5">
        {result.auto_send ? <AnsweredCard result={result} /> : <ForwardedCard result={result} />}
      </div>
    </div>
  );
}
