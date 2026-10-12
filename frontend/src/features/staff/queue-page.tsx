import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { ChevronRight, Inbox, Search, ShieldAlert } from "lucide-react";
import { usePreferences } from "@/app/preferences";
import { meOptions, staffListOptions } from "@/client/@tanstack/react-query.gen";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { OfficeId, Priority, StoredTicket } from "@/lib/types";
import type { QueueSearch } from "@/router";
import { PriorityBadge, timeAgo } from "./parts";

const PRIORITY_ORDER: Priority[] = ["urgent", "high", "medium", "low"];
const ALL = "all";

function Stat({ label, value, tone }: { label: string; value: number; tone?: "danger" }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p
        className={`mt-1 font-heading text-2xl font-bold tabular-nums ${tone === "danger" && value > 0 ? "text-destructive" : ""}`}
      >
        {value}
      </p>
    </div>
  );
}

function TicketRow({ ticket }: { ticket: StoredTicket }) {
  const { language, t } = usePreferences();
  return (
    <Link
      to="/staff/tickets/$ticketId"
      params={{ ticketId: String(ticket.id) }}
      className="group flex items-center gap-4 border-b px-4 py-3.5 transition-colors last:border-b-0 hover:bg-muted/50"
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <PriorityBadge priority={ticket.priority} />
          <span className="font-semibold text-foreground tabular-nums">#{ticket.id}</span>
          <span>{t.categories[ticket.category]}</span>
          <span aria-hidden>·</span>
          <span className="uppercase">{ticket.language}</span>
          {ticket.escalate && (
            <span className="inline-flex items-center gap-1 text-destructive">
              <ShieldAlert className="size-3.5" /> {t.staff.escalated}
            </span>
          )}
        </div>
        <p className="truncate text-sm">{ticket.text}</p>
        <p className="truncate text-xs text-muted-foreground">{t.offices[ticket.office]}</p>
      </div>
      <span className="hidden shrink-0 text-xs text-muted-foreground sm:block">
        {timeAgo(ticket.created_at, language)}
      </span>
      <ChevronRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

export function QueuePage() {
  const { t } = usePreferences();
  // The open queue refreshes itself every 15 s, so new tickets appear without reloading.
  const openQuery = useQuery({
    ...staffListOptions({ query: { status: "open" } }),
    refetchInterval: 15_000,
  });
  const handledQuery = useQuery(staffListOptions({ query: { status: "handled" } }));
  const isAdmin = useQuery(meOptions()).data?.role === "admin"; // staff only see their office
  const { q = "", office = ALL, priority = ALL } = useSearch({ from: "/staff/" });
  const navigate = useNavigate({ from: "/staff/" });
  const setFilter = (change: QueueSearch) =>
    navigate({ search: (current) => ({ ...current, ...change }), replace: true });

  const open = openQuery.data ?? []; // already sorted by the server: urgent first, then oldest
  const today = new Date().toDateString();
  const handledToday = (handledQuery.data ?? []).filter(
    (ticket) => ticket.handled_at && new Date(ticket.handled_at).toDateString() === today,
  ).length;
  const offices = Object.keys(t.offices) as OfficeId[];
  const shown = open
    .filter((ticket) => office === ALL || ticket.office === office)
    .filter((ticket) => priority === ALL || ticket.priority === priority)
    .filter((ticket) => ticket.text.toLocaleLowerCase().includes(q.toLocaleLowerCase()));

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 lg:px-8">
      <h1 className="font-heading text-2xl font-bold tracking-tight">{t.staff.queue}</h1>
      <div className="grid grid-cols-3 gap-3">
        <Stat label={t.staff.open} value={open.length} />
        <Stat
          label={t.staff.urgentOpen}
          value={open.filter((ticket) => ticket.priority === "urgent").length}
          tone="danger"
        />
        <Stat label={t.staff.handledToday} value={handledToday} />
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(event) => setFilter({ q: event.target.value || undefined })}
            placeholder={t.staff.search}
            aria-label={t.staff.search}
            className="pl-9"
          />
        </div>
        {isAdmin && (
          <Select
            value={office}
            onValueChange={(value) => setFilter({ office: offices.find((o) => o === value) })}
            items={{ [ALL]: t.staff.allOffices, ...t.offices }}
          >
            <SelectTrigger className="w-full sm:w-64" aria-label={t.staff.allOffices}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.staff.allOffices}</SelectItem>
              {offices.map((name) => (
                <SelectItem key={name} value={name}>
                  {t.offices[name]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Select
          value={priority}
          onValueChange={(value) =>
            setFilter({ priority: PRIORITY_ORDER.find((p) => p === value) })
          }
          items={{ [ALL]: t.staff.allPriorities, ...t.priorities }}
        >
          <SelectTrigger className="w-full sm:w-44" aria-label={t.staff.allPriorities}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t.staff.allPriorities}</SelectItem>
            {PRIORITY_ORDER.map((p) => (
              <SelectItem key={p} value={p}>
                {t.priorities[p]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="overflow-hidden rounded-xl border bg-card">
        {openQuery.isPending ? (
          ["a", "b", "c"].map((key) => (
            <div key={key} className="space-y-2 border-b px-4 py-4 last:border-b-0">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-full" />
            </div>
          ))
        ) : openQuery.isError ? (
          <div className="flex flex-col items-center gap-3 py-16 text-sm text-muted-foreground">
            {t.staff.loadError}
            <Button variant="outline" size="sm" onClick={() => openQuery.refetch()}>
              {t.staff.retry}
            </Button>
          </div>
        ) : shown.length === 0 ? (
          <p className="flex flex-col items-center gap-2 py-16 text-sm text-muted-foreground">
            <Inbox className="size-6" /> {t.staff.emptyQueue}
          </p>
        ) : (
          shown.map((ticket) => <TicketRow key={ticket.id} ticket={ticket} />)
        )}
      </div>
    </div>
  );
}
