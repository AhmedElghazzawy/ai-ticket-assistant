// The staff ticket page with the API faked: the history shows who did what.
import { expect, test } from "@playwright/test";
import type { Staff, StoredTicket, TicketEvent } from "../src/client/types.gen";

const ADMIN: Staff = {
  id: 1,
  email: "admin@bilecik.edu.tr",
  name: "Admin",
  role: "admin",
  office: null,
  demo: false,
};

const TICKET: StoredTicket = {
  id: 42,
  created_at: "2026-11-14T10:00:00Z",
  language: "tr",
  text: "Harç iadesi alabilir miyim?",
  category: "billing",
  priority: "medium",
  escalate: false,
  ai_reason: "Fee refund question.",
  office: "it",
  auto_send: false,
  reasons: [{ code: "not_covered" }],
  top_score: 0.71,
  draft: "Taslak cevap.",
  covered: false,
  sources: [],
  general_help: "",
  status: "open",
  final_reply: null,
  handled_at: null,
  demo: false,
  feedback: null,
  human_requested_at: null,
};

const HISTORY: TicketEvent[] = [
  {
    at: "2026-11-14T10:00:00Z",
    kind: "created",
    staff_name: null,
    from_office: null,
    to_office: "fees",
  },
  {
    at: "2026-11-14T10:05:00Z",
    kind: "reassigned",
    staff_name: "Ayşe",
    from_office: "fees",
    to_office: "it",
  },
];

test("the staff ticket page shows who moved the ticket and where", async ({ page }) => {
  await page.route("**/api/auth/me", (route) => route.fulfill({ json: ADMIN }));
  await page.route("**/api/staff/tickets?*", (route) => route.fulfill({ json: [TICKET] }));
  await page.route("**/api/staff/tickets/42", (route) => route.fulfill({ json: TICKET }));
  await page.route("**/api/staff/tickets/42/history", (route) => route.fulfill({ json: HISTORY }));
  await page.goto("/staff/tickets/42");
  await expect(page.getByText("Geçmiş")).toBeVisible();
  await expect(page.getByText("Talep oluşturuldu")).toBeVisible();
  await expect(page.getByText(/Başka birime aktarıldı: .*Harçlar.* → Bilgi İşlem/)).toBeVisible();
  await expect(page.getByText(/^Ayşe · /)).toBeVisible();
});
