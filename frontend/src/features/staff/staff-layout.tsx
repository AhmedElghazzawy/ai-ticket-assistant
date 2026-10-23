import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { ChartColumn, Inbox, LogOut, MessageSquare } from "lucide-react";
import { usePreferences } from "@/app/preferences";
import { logOut } from "@/client";
import { meOptions, staffListOptions } from "@/client/@tanstack/react-query.gen";
import { BrandMark, LanguageSwitch, ThemeMenu } from "@/components/app-header";
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";

/** Ends the session and empties the cache, so the next person at this computer sees nothing. */
function useLogout(): () => Promise<void> {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return async () => {
    await logOut();
    queryClient.clear();
    await navigate({ to: "/staff/login" });
  };
}

/** Who is logged in, and the logout button. */
function StaffCard() {
  const { t } = usePreferences();
  const { data: me } = useQuery(meOptions());
  const leave = useLogout();
  if (!me) return null;
  const initials = me.name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="flex items-center gap-2.5 px-1">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
        {initials}
      </span>
      <div className="min-w-0 flex-1 leading-tight">
        <p className="truncate text-sm font-medium">{me.name}</p>
        <p className="truncate text-xs text-muted-foreground">
          {me.office ? t.offices[me.office] : t.staff.allOfficesAdmin}
        </p>
      </div>
      <Button variant="ghost" size="icon-sm" onClick={leave} aria-label={t.staff.logOut}>
        <LogOut />
      </Button>
    </div>
  );
}

function OpenCount() {
  const { data } = useQuery(staffListOptions({ query: { status: "open" } }));
  if (!data) return null;
  return (
    <span className="ml-auto rounded-md bg-primary px-1.5 text-xs font-semibold text-primary-foreground tabular-nums">
      {data.length}
    </span>
  );
}

function Sidebar() {
  const { t } = usePreferences();
  const item =
    "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors";
  return (
    <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r bg-sidebar lg:flex">
      <div className="flex items-center gap-3 px-4 py-4">
        <BrandMark />
        <div className="leading-tight">
          <p className="font-heading text-sm font-bold">{t.staff.console}</p>
          <p className="text-xs text-muted-foreground">BŞEÜ</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        <Link
          to="/staff"
          activeOptions={{ exact: true }}
          className={`${item} text-muted-foreground hover:bg-sidebar-accent hover:text-foreground`}
          activeProps={{ className: "bg-sidebar-accent text-foreground" }}
        >
          <Inbox className="size-4" /> {t.staff.queue} <OpenCount />
        </Link>
        <span className={`${item} cursor-not-allowed text-muted-foreground/60`}>
          <ChartColumn className="size-4" /> {t.staff.insights}
          <span className="ml-auto text-[0.65rem] uppercase">{t.staff.soon}</span>
        </span>
      </nav>
      <div className="space-y-3 border-t p-3">
        <Link
          to="/"
          className={`${item} text-muted-foreground hover:bg-sidebar-accent hover:text-foreground`}
        >
          <MessageSquare className="size-4" /> {t.staff.studentView}
        </Link>
        <StaffCard />
        <div className="flex items-center justify-between px-1">
          <LanguageSwitch />
          <ThemeMenu />
        </div>
      </div>
    </aside>
  );
}

/** A clear note in demo mode, so nobody takes sample tickets for real student messages. */
function DemoBanner() {
  const { t } = usePreferences();
  const { data: me } = useQuery(meOptions());
  if (!me?.demo) return null;
  return (
    <p className="border-b bg-muted/50 px-4 py-2 text-center text-xs font-medium text-warning-foreground lg:px-8 dark:text-warning">
      {t.staff.demoBanner}
    </p>
  );
}

function MobileLogout() {
  const { t } = usePreferences();
  const leave = useLogout();
  return (
    <Button variant="ghost" size="icon" aria-label={t.staff.logOut} onClick={leave}>
      <LogOut />
    </Button>
  );
}

function MobileBar() {
  const { t } = usePreferences();
  return (
    <header className="sticky top-0 z-10 flex h-14 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-md lg:hidden">
      <BrandMark />
      <Link to="/staff" className="font-heading text-sm font-bold">
        {t.staff.console}
      </Link>
      <div className="ml-auto flex items-center gap-1.5">
        <LanguageSwitch />
        <ThemeMenu />
        <MobileLogout />
      </div>
    </header>
  );
}

export function StaffLayout() {
  return (
    <>
      <div className="flex min-h-dvh">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <MobileBar />
          <DemoBanner />
          <Outlet />
        </div>
      </div>
      <Toaster position="bottom-right" />
    </>
  );
}
