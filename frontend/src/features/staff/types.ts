// A forwarded ticket as the staff console sees it. Planned API shape: the backend will send
// reason CODES with their data instead of English sentences, so the page can translate them.

import type { Category, Language, OfficeId, Priority } from "@/lib/types";

export type Reason =
  | { code: "category_other" }
  | { code: "escalation" }
  | { code: "urgent" }
  | { code: "weak_match"; score: number; min: number }
  | { code: "not_covered" }
  | { code: "no_citation" };

export interface StaffSource {
  id: string; // e.g. "harc_ucretler.tr#5"
  title: string;
  section: string;
  url: string | null;
}

export type Status = "open" | "handled";

export interface StaffTicket {
  id: number;
  created_at: string; // ISO time
  language: Language;
  text: string;
  category: Category;
  priority: Priority;
  escalate: boolean;
  ai_reason: string; // the model's own explanation of its labels (always English)
  office: OfficeId; // an ID; the page shows the name in the staff member's language
  reasons: Reason[];
  top_score: number;
  draft: string;
  sources: StaffSource[];
  status: Status;
  final_reply?: string;
}
