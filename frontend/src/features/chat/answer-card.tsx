import {
  ArrowUpRight,
  BadgeCheck,
  Building2,
  Clock,
  FileText,
  Forward,
  Phone,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { usePreferences } from "@/app/preferences";
import { Button } from "@/components/ui/button";
import type { StoredSource, TicketOut } from "@/lib/types";

function SourceCard({ source }: { source: StoredSource }) {
  const body = (
    <>
      <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
        <FileText className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{source.section}</span>
        <span className="block truncate text-xs text-muted-foreground">{source.title}</span>
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
      <div className="grid gap-2 sm:grid-cols-2">
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
      <span className="font-semibold tabular-nums text-foreground">
        {t.ticketNo} #{result.ticket_id}
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

function AnsweredCard({ result }: { result: TicketOut }) {
  const { t } = usePreferences();
  return (
    <div className="space-y-4">
      <p className="flex items-center gap-1.5 text-xs font-semibold text-success">
        <BadgeCheck className="size-4" /> {t.answered}
      </p>
      <p className="text-[0.95rem] leading-relaxed">{result.reply}</p>
      <SourceList sources={result.sources} />
      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <TicketMeta result={result} />
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <span className="mr-1">{t.helpful}</span>
          <Button variant="ghost" size="icon-sm" aria-label="👍">
            <ThumbsUp />
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label="👎">
            <ThumbsDown />
          </Button>
        </div>
      </div>
    </div>
  );
}

function ForwardedCard({ result }: { result: TicketOut }) {
  const { t } = usePreferences();
  return (
    <div className="space-y-4">
      <p className="flex items-center gap-1.5 text-xs font-semibold text-warning-foreground dark:text-warning">
        <Forward className="size-4" /> {t.forwarded}
      </p>
      {result.first_help && result.reply ? (
        // Forwarded, but the cited part of the draft passed every safety check (decision.show_first_help).
        <div className="space-y-3 rounded-lg border bg-background p-3.5">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-success">
            <BadgeCheck className="size-4" /> {t.firstHelp}
          </p>
          <p className="text-[0.95rem] leading-relaxed">{result.reply}</p>
          <p className="text-xs text-muted-foreground">{t.firstHelpNote}</p>
          <SourceList sources={result.sources} />
        </div>
      ) : (
        <p className="text-[0.95rem] leading-relaxed">{t.forwardedText}</p>
      )}
      <div className="space-y-3 rounded-lg border border-warning/40 bg-warning/10 p-3.5">
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
