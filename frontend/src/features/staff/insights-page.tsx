// Staff statistics. Charts follow the dataviz skill: form first (stat tiles, one stacked bar,
// one-series bars), validated series colors from index.css, thin marks with 4px rounded data
// ends and 2px gaps, a tooltip on every mark, text in text colors, and a table view for every
// chart. Plain HTML and CSS: three small charts do not justify a chart library.
import { useQuery } from "@tanstack/react-query";
import { Table2 } from "lucide-react";
import { type CSSProperties, type ReactNode, useState } from "react";
import { usePreferences } from "@/app/preferences";
import { staffInsightsOptions } from "@/client/@tanstack/react-query.gen";
import type { StaffInsightsResponse } from "@/client/types.gen";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { Category } from "@/lib/types";
import { cn } from "@/lib/utils";

type Insights = StaffInsightsResponse;
type Outcome = keyof Insights["outcomes"];

const OUTCOME_COLOR: Record<Outcome, string> = {
  auto_sent: "bg-series-auto",
  first_help_waiting: "bg-series-first-help",
  waiting: "bg-series-waiting",
  handled: "bg-series-handled",
};
const OUTCOME_ORDER: Outcome[] = ["auto_sent", "first_help_waiting", "waiting", "handled"];

const percent = (part: number, whole: number) =>
  whole === 0 ? "–" : `${Math.round((100 * part) / whole)}%`;

function Tile({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-heading text-2xl font-semibold">{value}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{note}</p>
    </div>
  );
}

/** One mark with its tooltip. The mark itself is a button: focusable, announced to screen
 *  readers with its value, and the hit target (value first, label second in the tooltip). */
function Mark({
  value,
  label,
  className,
  style,
}: {
  value: string;
  label: string;
  className: string;
  style: CSSProperties;
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={<button type="button" aria-label={`${label}: ${value}`} style={style} />}
        className={cn(
          "block outline-none transition-opacity hover:opacity-80 focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
      />
      <TooltipContent>
        <span className="font-semibold">{value}</span>
        <span className="opacity-70">{label}</span>
      </TooltipContent>
    </Tooltip>
  );
}

function DataTable({ rows, headers }: { rows: [string, string, string?][]; headers: string[] }) {
  return (
    <table className="mt-4 w-full text-left text-sm">
      <thead className="text-xs text-muted-foreground">
        <tr>
          {headers.map((header) => (
            <th key={header} className="border-b py-1.5 font-medium">
              {header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="tabular-nums">
        {rows.map(([name, ...values]) => (
          <tr key={name}>
            <td className="border-b py-1.5">{name}</td>
            {values.map((value) => (
              <td key={value} className="border-b py-1.5">
                {value}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border bg-card p-5">
      <h2 className="font-heading text-sm font-bold">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function OutcomesBar({ data, table }: { data: Insights; table: boolean }) {
  const { t } = usePreferences();
  const texts = t.staff.insightsPage;
  const shown = OUTCOME_ORDER.filter((key) => data.outcomes[key] > 0);
  return (
    <Card title={texts.outcomesTitle}>
      {/* part-to-whole: one stacked bar, 2px surface gaps, rounded only at the two outer ends */}
      <div className="flex h-6 gap-[2px] overflow-hidden rounded-[4px]">
        {shown.map((key) => (
          <Mark
            key={key}
            value={`${data.outcomes[key]} · ${percent(data.outcomes[key], data.total)}`}
            label={texts.outcomes[key]}
            style={{ flexGrow: data.outcomes[key] }}
            className={cn("h-6 basis-0", OUTCOME_COLOR[key])}
          />
        ))}
      </div>
      {/* legend: always present for 2+ series, each key a swatch beside text-colored labels */}
      <ul className="mt-4 grid gap-x-12 gap-y-2 sm:grid-cols-2">
        {OUTCOME_ORDER.map((key) => (
          <li key={key} className="flex items-center gap-2 text-sm">
            <span className={cn("size-2.5 shrink-0 rounded-[2px]", OUTCOME_COLOR[key])} />
            <span className="text-muted-foreground">{texts.outcomes[key]}</span>
            <span className="ml-auto font-semibold tabular-nums">
              {data.outcomes[key]}
              <span className="ml-1.5 font-normal text-muted-foreground">
                {percent(data.outcomes[key], data.total)}
              </span>
            </span>
          </li>
        ))}
      </ul>
      {table && (
        <DataTable
          headers={["", texts.count, texts.share]}
          rows={OUTCOME_ORDER.map((key) => [
            texts.outcomes[key],
            String(data.outcomes[key]),
            percent(data.outcomes[key], data.total),
          ])}
        />
      )}
    </Card>
  );
}

function CategoryBars({ data, table }: { data: Insights; table: boolean }) {
  const { t } = usePreferences();
  const texts = t.staff.insightsPage;
  const rows = (Object.entries(data.by_category) as [Category, number][]).sort(
    (a, b) => b[1] - a[1],
  );
  const max = Math.max(1, ...rows.map(([, count]) => count));
  return (
    <Card title={texts.byCategoryTitle}>
      <ul className="space-y-2.5">
        {rows.map(([category, count]) => (
          <li key={category} className="grid grid-cols-[9rem_1fr] items-center gap-3 text-sm">
            <span className="truncate text-muted-foreground">{t.categories[category]}</span>
            <div className="flex items-center gap-2">
              <Mark
                value={String(count)}
                label={t.categories[category]}
                style={{ width: `${(100 * count) / max}%` }}
                className={cn("h-3 rounded-r-[4px] bg-series-single", count === 0 && "invisible")}
              />
              <span className="font-semibold tabular-nums">{count}</span>
            </div>
          </li>
        ))}
      </ul>
      {table && (
        <DataTable
          headers={["", texts.count]}
          rows={rows.map(([category, count]) => [t.categories[category], String(count)])}
        />
      )}
    </Card>
  );
}

function DayColumns({ data, table }: { data: Insights; table: boolean }) {
  const { t, language } = usePreferences();
  const texts = t.staff.insightsPage;
  const max = Math.max(1, ...data.by_day.map((day) => day.count));
  const label = (day: string) =>
    new Date(`${day}T00:00:00Z`).toLocaleDateString(language === "tr" ? "tr-TR" : "en-GB", {
      day: "numeric",
      month: "short",
      timeZone: "UTC",
    });
  return (
    <Card title={texts.byDayTitle}>
      <div className="flex h-36 items-end gap-[2px] border-b">
        {data.by_day.map((day) => (
          <div key={day.day} className="flex h-full flex-1 items-end justify-center">
            <Mark
              value={String(day.count)}
              label={label(day.day)}
              style={{ height: `${(100 * day.count) / max}%` }}
              className={cn(
                "w-full max-w-6 rounded-t-[4px] bg-series-single",
                day.count === 0 && "invisible", // a zero is no mark: the baseline says it
              )}
            />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[0.7rem] text-muted-foreground tabular-nums">
        <span>{label(data.by_day[0]?.day ?? "")}</span>
        <span>{label(data.by_day.at(-1)?.day ?? "")}</span>
      </div>
      {table && (
        <DataTable
          headers={[texts.day, texts.count]}
          rows={data.by_day.map((day) => [label(day.day), String(day.count)])}
        />
      )}
    </Card>
  );
}

export function InsightsPage() {
  const { t } = usePreferences();
  const texts = t.staff.insightsPage;
  const insights = useQuery(staffInsightsOptions());
  const [table, setTable] = useState(false);
  const data = insights.data;

  return (
    <TooltipProvider>
      <div className="space-y-6 p-4 lg:p-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-heading text-2xl font-bold tracking-tight">{texts.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{texts.subtitle}</p>
          </div>
          <Button variant="outline" size="sm" aria-pressed={table} onClick={() => setTable(!table)}>
            <Table2 /> {table ? texts.hideTable : texts.showTable}
          </Button>
        </div>
        {!data ? (
          <div className="grid gap-3 sm:grid-cols-3">
            {[1, 2, 3].map((n) => (
              <Skeleton key={n} className="h-24" />
            ))}
          </div>
        ) : data.total === 0 ? (
          <p className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
            {texts.empty}
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              <Tile
                label={texts.total}
                value={String(data.total)}
                note={texts.sample(data.total)}
              />
              <Tile
                label={texts.autoRate}
                value={percent(data.outcomes.auto_sent, data.total)}
                note={texts.sample(data.total)}
              />
              <Tile
                label={texts.helpedNow}
                value={percent(data.outcomes.auto_sent + data.first_help_total, data.total)}
                note={texts.helpedNowNote}
              />
              <Tile
                label={texts.waiting}
                value={String(data.outcomes.first_help_waiting + data.outcomes.waiting)}
                note={texts.sample(data.total)}
              />
              <Tile
                label={texts.medianReply}
                value={
                  data.median_reply_minutes === null
                    ? "–"
                    : texts.minutes(data.median_reply_minutes)
                }
                note={data.handled_n ? texts.sample(data.handled_n) : texts.noData}
              />
              <Tile
                label={texts.helpfulRate}
                value={percent(data.feedback_helpful, data.feedback_n)}
                note={data.feedback_n ? texts.sample(data.feedback_n) : texts.noData}
              />
            </div>
            <OutcomesBar data={data} table={table} />
            <div className="grid gap-6 lg:grid-cols-2">
              <CategoryBars data={data} table={table} />
              <DayColumns data={data} table={table} />
            </div>
          </>
        )}
      </div>
    </TooltipProvider>
  );
}
