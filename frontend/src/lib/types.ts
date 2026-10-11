// Short names for the API's types. Everything here comes from the GENERATED client
// (src/client, built from FastAPI's OpenAPI schema), so it can never drift from the backend.

import type { StoredSource, StoredTicket, TicketIn, TicketOut } from "@/client";

export type { StoredSource, StoredTicket, TicketOut };
export type Language = TicketIn["language"];
export type Category = TicketOut["category"];
export type Priority = TicketOut["priority"];
export type OfficeId = TicketOut["office"];
export type Reason = StoredTicket["reasons"][number];
export type Status = StoredTicket["status"];
