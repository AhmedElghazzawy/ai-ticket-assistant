import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowUpRight,
  Bot,
  CircleCheck,
  FileText,
  Send,
  ShieldAlert,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { usePreferences } from "@/app/preferences";
import { staffReply } from "@/client";
import { staffGetOptions, staffReassignMutation } from "@/client/@tanstack/react-query.gen";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { OfficeId, StoredSource, StoredTicket } from "@/lib/types";
import { PriorityBadge, ReasonList, timeAgo } from "./parts";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3 rounded-xl border bg-card p-4 sm:p-5">
      <h2 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
        {title}
      </h2>
      {children}
    </section>
  );
}

function SourceItem({ source }: { source: StoredSource }) {
  return (
    <li className="flex items-start gap-3 rounded-lg border bg-background p-3">
      <FileText className="mt-0.5 size-4 shrink-0 text-accent-foreground" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{source.section}</p>
        <p className="truncate text-xs text-muted-foreground">{source.title}</p>
        <p className="mt-1 font-mono text-[0.7rem] text-muted-foreground">{source.id}</p>
      </div>
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={source.title}
        className="text-muted-foreground hover:text-foreground"
      >
        <ArrowUpRight className="size-4" />
      </a>
    </li>
  );
}

/** The editable reply. A draft is only offered when the documents really answer the ticket. */
function ReplyEditor({ ticket }: { ticket: StoredTicket }) {
  const { t } = usePreferences();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [reply, setReply] = useState(ticket.covered ? ticket.draft : "");
  const send = useMutation({
    mutationFn: async (text: string) => {
      const { data, response } = await staffReply({
        path: { ticket_id: ticket.id },
        body: { reply: text },
      });
      if (response?.status === 409) throw new Error(t.staff.alreadyHandled); // someone was faster
      if (!data) throw new Error(t.staff.sendError);
      return data;
    },
    onSuccess: () => {
      toast.success(t.staff.sent, { description: t.staff.sentNote });
      void navigate({ to: "/staff" });
    },
    onError: (error) => toast.error(error.message),
    onSettled: () => queryClient.invalidateQueries(), // queue and ticket are re-read from the server
  });

  if (ticket.status === "handled") {
    return (
      <Panel title={t.staff.handled}>
        <p className="flex items-center gap-2 text-sm font-medium text-success">
          <CircleCheck className="size-4" /> {t.staff.sent}
        </p>
        <p className="text-sm whitespace-pre-wrap">{ticket.final_reply}</p>
      </Panel>
    );
  }

  return (
    <Panel title={t.staff.reply}>
      <p className="flex gap-2 text-xs text-muted-foreground">
        <Bot className="size-4 shrink-0" /> {ticket.covered ? t.staff.replyHint : t.staff.noDraft}
      </p>
      <Textarea
        value={reply}
        onChange={(event) => setReply(event.target.value)}
        rows={8}
        aria-label={t.staff.reply}
        className="text-[0.95rem] leading-relaxed"
      />
      <div className="flex justify-end">
        <Button
          onClick={() => send.mutate(reply.trim())}
          disabled={!reply.trim() || send.isPending}
        >
          <Send /> {t.staff.send}
        </Button>
      </div>
    </Panel>
  );
}

function OfficeSelect({ ticket }: { ticket: StoredTicket }) {
  const { t } = usePreferences();
  const queryClient = useQueryClient();
  const reassign = useMutation({
    ...staffReassignMutation(),
    onSettled: () => queryClient.invalidateQueries(),
  });
  const offices = Object.keys(t.offices) as OfficeId[];
  return (
    <Select
      value={ticket.office}
      onValueChange={(value) => {
        const office = offices.find((o) => o === value);
        if (office) reassign.mutate({ path: { ticket_id: ticket.id }, body: { office } });
      }}
      items={t.offices}
    >
      <SelectTrigger className="w-full min-w-0" aria-label={t.staff.reassign}>
        <SelectValue className="truncate" />
      </SelectTrigger>
      <SelectContent>
        {offices.map((name) => (
          <SelectItem key={name} value={name}>
            {t.offices[name]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function TicketPage() {
  const { language, t } = usePreferences();
  const { ticketId } = useParams({ from: "/staff/tickets/$ticketId" });
  const query = useQuery(staffGetOptions({ path: { ticket_id: Number(ticketId) } }));
  const ticket = query.data;

  if (query.isPending) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 lg:px-8">
        <Skeleton className="h-8 w-40" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="px-4 py-16 text-center text-sm text-muted-foreground">
        #{ticketId}: {t.staff.notFound}{" "}
        <Link to="/staff" className="underline">
          {t.staff.back}
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 lg:px-8">
      <div className="space-y-3">
        <Link
          to="/staff"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> {t.staff.back}
        </Link>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="font-heading text-2xl font-bold tracking-tight tabular-nums">
            #{ticket.id}
          </h1>
          <PriorityBadge priority={ticket.priority} />
          {ticket.escalate && (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-destructive">
              <ShieldAlert className="size-3.5" /> {t.staff.escalated}
            </span>
          )}
          <span className="text-sm text-muted-foreground">
            {t.staff.received} {timeAgo(ticket.created_at, language)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <div className="space-y-6">
          <Panel title={t.staff.studentMessage}>
            <p className="text-[0.95rem] leading-relaxed whitespace-pre-wrap">{ticket.text}</p>
            <p className="text-xs text-muted-foreground uppercase">{ticket.language}</p>
          </Panel>
          <Panel title={t.staff.whyForwarded}>
            <ReasonList reasons={ticket.reasons} />
          </Panel>
          <Panel title={t.staff.aiAnalysis}>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">{t.staff.category}</dt>
                <dd className="font-medium">{t.categories[ticket.category]}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">{t.staff.reassign}</dt>
                <dd className="pt-1">
                  <OfficeSelect ticket={ticket} />
                </dd>
              </div>
            </dl>
            <blockquote className="border-l-2 pl-3 text-sm text-muted-foreground italic">
              {ticket.ai_reason}
              <footer className="mt-1 text-xs not-italic">{t.staff.aiReasonNote}</footer>
            </blockquote>
          </Panel>
        </div>
        <div className="space-y-6">
          <ReplyEditor key={ticket.id} ticket={ticket} />
          <Panel title={t.staff.sourcesUsed}>
            {ticket.sources.length > 0 ? (
              <ul className="space-y-2">
                {ticket.sources.map((source) => (
                  <SourceItem key={source.id} source={source} />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">{t.staff.noSources}</p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
