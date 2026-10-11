// Mirrors the API's TicketOut (src/api.py). Temporary: in the next step this file is
// replaced by types generated from FastAPI's OpenAPI schema, so the two can never drift.

export type Language = "tr" | "en";

export type Category =
  | "account_access"
  | "it_support"
  | "registration"
  | "academic_records"
  | "billing"
  | "campus_life"
  | "other";

export type Priority = "low" | "medium" | "high" | "urgent";

export interface Source {
  title: string;
  section: string;
  url?: string; // planned: the API will send the official link stored in each document
}

export interface TicketOut {
  ticket_id: number;
  category: Category;
  priority: Priority;
  office: string;
  auto_send: boolean;
  reply: string | null; // null: a human answers, the unchecked AI draft never reaches the browser
  sources: Source[];
  emergency: boolean; // urgent and escalated: show the 112 line
}
