// The staff console's data for the prototype: real forwarded dev tickets (built from
// tickets.jsonl, eval/results_high.json and eval/pipeline_results_dev.json). Replaced by
// API calls (TanStack Query) when the console is connected to the backend.

import { createContext, type ReactNode, use, useState } from "react";
import type { OfficeId } from "@/lib/types";
import tickets from "@/mocks/staff-tickets.json";
import type { StaffTicket } from "./types";

interface StaffStore {
  tickets: StaffTicket[];
  handle: (id: number, reply: string) => void;
  reassign: (id: number, office: OfficeId) => void;
}

const StoreContext = createContext<StaffStore | null>(null);

/** Shift the saved times so the newest ticket arrived a few minutes ago. */
function freshTickets(): StaffTicket[] {
  const saved = tickets as Omit<StaffTicket, "status">[];
  const newest = Math.max(...saved.map((t) => Date.parse(t.created_at)));
  const shift = Date.now() - newest;
  return saved.map((t) => ({
    ...t,
    created_at: new Date(Date.parse(t.created_at) + shift).toISOString(),
    status: "open",
  }));
}

export function StaffStoreProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState(freshTickets);
  const update = (id: number, change: Partial<StaffTicket>) =>
    setItems((current) => current.map((t) => (t.id === id ? { ...t, ...change } : t)));

  return (
    <StoreContext
      value={{
        tickets: items,
        handle: (id, reply) => update(id, { status: "handled", final_reply: reply }),
        reassign: (id, office) => update(id, { office }),
      }}
    >
      {children}
    </StoreContext>
  );
}

export function useStaffStore(): StaffStore {
  const store = use(StoreContext);
  if (!store) throw new Error("useStaffStore must be used inside StaffStoreProvider");
  return store;
}
