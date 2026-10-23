// The staff Insights page with the API faked (login check, queue count, statistics).
import { expect, test } from "@playwright/test";
import type { Staff, StaffInsightsResponse } from "../src/client/types.gen";

const ADMIN: Staff = {
  id: 1,
  email: "admin@bilecik.edu.tr",
  name: "Admin",
  role: "admin",
  office: null,
  demo: false,
};

const INSIGHTS: StaffInsightsResponse = {
  total: 10,
  outcomes: { auto_sent: 4, first_help_waiting: 2, waiting: 1, handled: 3 },
  first_help_total: 3,
  median_reply_minutes: 95,
  handled_n: 3,
  feedback_helpful: 3,
  feedback_n: 4,
  by_category: {
    account_access: 2,
    it_support: 1,
    registration: 3,
    academic_records: 2,
    billing: 2,
    campus_life: 0,
    other: 0,
  },
  by_day: Array.from({ length: 14 }, (_, n) => ({
    day: `2026-10-${String(10 + n).padStart(2, "0")}`,
    count: n % 3,
  })),
};

test("insights show every number with its sample size, and a table view", async ({ page }) => {
  await page.route("**/api/auth/me", (route) => route.fulfill({ json: ADMIN }));
  await page.route("**/api/staff/tickets*", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/staff/insights", (route) => route.fulfill({ json: INSIGHTS }));
  await page.goto("/staff/insights");
  await expect(page.getByRole("heading", { name: "İstatistikler" })).toBeVisible();
  await expect(page.getByText("70%")).toBeVisible(); // helped right away: (4 + 3) / 10
  await expect(page.getByText("1.6 sa")).toBeVisible(); // median reply time, 95 minutes
  await expect(page.getByText("75%")).toBeVisible(); // found helpful: 3 of 4
  await expect(page.getByText("n = 4")).toBeVisible();
  await expect(page.getByRole("button", { name: "Ders Kaydı: 3" })).toBeVisible(); // each mark is labeled
  await page.getByRole("button", { name: "Tablo olarak göster" }).click();
  await expect(page.getByRole("table")).toHaveCount(3);
});
