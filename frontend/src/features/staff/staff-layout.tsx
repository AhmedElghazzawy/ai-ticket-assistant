import { Link, Outlet } from "@tanstack/react-router";
import { ChartColumn, Inbox, MessageSquare } from "lucide-react";
import { usePreferences } from "@/app/preferences";
import { BrandMark, LanguageSwitch, ThemeMenu } from "@/components/app-header";
import { Toaster } from "@/components/ui/sonner";
import { StaffStoreProvider, useStaffStore } from "./store";

function OpenCount() {
  const { tickets } = useStaffStore();
  const open = tickets.filter((ticket) => ticket.status === "open").length;
  return (
    <span className="ml-auto rounded-md bg-primary px-1.5 text-xs font-semibold text-primary-foreground tabular-nums">
      {open}
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
        <div className="flex items-center gap-2.5 px-1">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
            DP
          </span>
          <p className="min-w-0 flex-1 truncate text-sm font-medium">{t.staff.signedInAs}</p>
        </div>
        <div className="flex items-center justify-between px-1">
          <LanguageSwitch />
          <ThemeMenu />
        </div>
      </div>
    </aside>
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
      </div>
    </header>
  );
}

export function StaffLayout() {
  return (
    <StaffStoreProvider>
      <div className="flex min-h-dvh">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <MobileBar />
          <Outlet />
        </div>
      </div>
      <Toaster position="bottom-right" />
    </StaffStoreProvider>
  );
}
