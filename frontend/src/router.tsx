// The page addresses. Staff pages are loaded only when someone opens /staff
// (code splitting), so students never download the staff console.

import {
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
  Outlet,
} from "@tanstack/react-router";
import { ChatPage } from "@/features/chat/chat-page";
import type { OfficeId, Priority } from "@/lib/types";

const PRIORITIES: readonly string[] = ["low", "medium", "high", "urgent"] satisfies Priority[];
const OFFICES: readonly string[] = [
  "it",
  "student_affairs",
  "fees",
  "sks",
  "duty",
] satisfies OfficeId[];

export interface QueueSearch {
  q?: string;
  office?: OfficeId;
  priority?: Priority;
}

/** Queue filters live in the URL; anything invalid there (e.g. ?priority=banana) is ignored. */
function validateQueueSearch(search: Record<string, unknown>): QueueSearch {
  const text = (value: unknown) => (typeof value === "string" && value ? value : undefined);
  return {
    q: text(search.q),
    office: OFFICES.includes(String(search.office)) ? (search.office as OfficeId) : undefined,
    priority: PRIORITIES.includes(String(search.priority))
      ? (search.priority as Priority)
      : undefined,
  };
}

const rootRoute = createRootRoute({ component: Outlet });

const chatRoute = createRoute({ getParentRoute: () => rootRoute, path: "/", component: ChatPage });

const staffRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/staff",
  component: lazyRouteComponent(() => import("@/features/staff/staff-layout"), "StaffLayout"),
});

const queueRoute = createRoute({
  getParentRoute: () => staffRoute,
  path: "/",
  validateSearch: validateQueueSearch,
  component: lazyRouteComponent(() => import("@/features/staff/queue-page"), "QueuePage"),
});

const ticketRoute = createRoute({
  getParentRoute: () => staffRoute,
  path: "/tickets/$ticketId",
  component: lazyRouteComponent(() => import("@/features/staff/ticket-page"), "TicketPage"),
});

const routeTree = rootRoute.addChildren([
  chatRoute,
  staffRoute.addChildren([queueRoute, ticketRoute]),
]);

export const router = createRouter({ routeTree, defaultPreload: "intent" });

// Lets TypeScript check every <Link to="..."> and route parameter in the whole app.
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
