import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { CircleCheck, Clock, Inbox, MessageSquareReply, RefreshCw } from "lucide-react";
import { usePreferences } from "@/app/preferences";
import { lookupTicket } from "@/client";
import { AppHeader } from "@/components/app-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { loadMyTickets, type MyTicket } from "@/lib/my-tickets";
import { cn } from "@/lib/utils";

const STATUS_STYLE = {
  auto_sent: "text-success",
  open: "text-warning-foreground dark:text-warning",
  handled: "text-success",
} as const;

function TicketStatus({ ticket }: { ticket: MyTicket }) {
  const { t, language } = usePreferences();
  const status = useQuery({
    queryKey: ["my-ticket", ticket.id],
    queryFn: async () => {
      const { data } = await lookupTicket({ body: { ticket_id: ticket.id, code: ticket.code } });
      return data ?? null; // null: wrong code or removed (e.g. the demo database was reset)
    },
  });
  const date = new Date(ticket.createdAt).toLocaleString(language === "tr" ? "tr-TR" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <li className="rounded-2xl border bg-card p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span className="font-mono font-semibold text-foreground">#{ticket.id}</span>
        <span>{date}</span>
      </div>
      <p className="mt-2 line-clamp-2 text-[0.95rem]">{ticket.question}</p>
      <div className="mt-4 border-t pt-3">
        {status.isPending ? (
          <Skeleton className="h-5 w-40" />
        ) : status.data ? (
          <div className="space-y-3">
            <p
              className={cn(
                "flex items-center gap-1.5 text-sm font-semibold",
                STATUS_STYLE[status.data.status],
              )}
            >
              {status.data.status === "open" ? (
                <Clock className="size-4" />
              ) : (
                <CircleCheck className="size-4" />
              )}
              {t.statusLabels[status.data.status]} · {t.offices[status.data.office]}
            </p>
            {status.data.reply ? (
              <div className="rounded-lg border bg-muted/40 p-3.5">
                <p className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                  <MessageSquareReply className="size-3.5" />
                  {status.data.status === "handled" ? t.statusLabels.handled : t.answered}
                </p>
                <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">
                  {status.data.reply}
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t.waiting}</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t.ticketGone}</p>
        )}
      </div>
    </li>
  );
}

export function MyTicketsPage() {
  const { t } = usePreferences();
  const navigate = useNavigate();
  const tickets = loadMyTickets();
  const queryClient = useQueryClient();

  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader onNewChat={() => navigate({ to: "/" })} />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          {t.myTicketsTitle}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">{t.myTicketsText}</p>
        {tickets.length === 0 ? (
          <div className="mt-10 flex flex-col items-center gap-4 rounded-2xl border border-dashed p-10 text-center">
            <Inbox className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">{t.myTicketsEmpty}</p>
            <Button render={<Link to="/" />}>{t.backToChat}</Button>
          </div>
        ) : (
          <>
            <div className="mt-6 flex justify-end">
              <Button
                variant="outline"
                size="sm" // every ticket query starts with ["my-ticket"], so one call refreshes them all
                onClick={() => queryClient.invalidateQueries({ queryKey: ["my-ticket"] })}
              >
                <RefreshCw /> {t.checkStatus}
              </Button>
            </div>
            <ul className="mt-3 space-y-3">
              {tickets.map((ticket) => (
                <TicketStatus key={ticket.id} ticket={ticket} />
              ))}
            </ul>
          </>
        )}
      </main>
    </div>
  );
}
