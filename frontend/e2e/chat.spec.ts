// What a student sees for each kind of answer. The API is faked, so these test the page only.
import { expect, type Page, test } from "@playwright/test";
import type { TicketOut } from "../src/lib/types";

const SOURCE = {
  id: "sinavlar.tr#3",
  title: "Sınavlar",
  section: "Sınav programı ve sınava giriş (Madde 19)",
  source: "Resmî olmayan kaynak: örnek rehber",
  url: "https://example.edu/sinavlar.pdf",
};

const BASE: TicketOut = {
  ticket_id: 42,
  category: "academic_records",
  priority: "low",
  office: "student_affairs",
  auto_send: false,
  first_help: false,
  reply: null,
  sources: [],
  emergency: false,
  access_code: "secret-code-1234567890",
};

async function askWithAnswer(page: Page, answer: Partial<TicketOut>) {
  await page.route("**/api/tickets", (route) => route.fulfill({ json: { ...BASE, ...answer } }));
  await page.goto("/");
  await page.getByRole("textbox").fill("Sınav programı nerede?");
  await page.getByRole("textbox").press("Enter");
}

test("the page says it is a student project, not an official service", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("resmî bir BŞEÜ hizmeti değildir").first()).toBeVisible();
});

test("an auto-sent answer shows the reply and its source", async ({ page }) => {
  await askWithAnswer(page, {
    auto_send: true,
    reply: "Program OBS'de ilan edilir.",
    sources: [SOURCE],
  });
  await expect(page.getByText("Program OBS'de ilan edilir.")).toBeVisible();
  await expect(page.getByRole("link", { name: /Sınav programı/ })).toHaveAttribute(
    "href",
    SOURCE.url,
  );
  await expect(page.getByText("Talep no #42")).toBeVisible();
  await expect(page.getByText("Resmî olmayan kaynak: örnek rehber")).toBeVisible();
});

test("a forwarded ticket with first help shows the cited part", async ({ page }) => {
  await askWithAnswer(page, {
    first_help: true,
    reply: "Program OBS'de ilan edilir.",
    sources: [SOURCE],
  });
  await expect(page.getByText("Ön bilgi")).toBeVisible();
  await expect(page.getByText("Program OBS'de ilan edilir.")).toBeVisible();
  await expect(page.getByText("İlgili birime iletildi")).toBeVisible();
});

test("an urgent escalation shows the 112 line and no AI text", async ({ page }) => {
  await askWithAnswer(page, { priority: "urgent", emergency: true, office: "duty" });
  await expect(page.getByRole("link", { name: /112/ })).toHaveAttribute("href", "tel:112");
  await expect(page.getByText("Ön bilgi")).toHaveCount(0);
});

test("feedback is sent with the ticket's secret code", async ({ page }) => {
  let sent: unknown = null;
  await page.route("**/api/tickets/42/feedback", async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ status: 204 });
  });
  await askWithAnswer(page, {
    auto_send: true,
    reply: "Program OBS'de ilan edilir.",
    sources: [SOURCE],
  });
  await page.getByRole("button", { name: "Evet, işime yaradı" }).click();
  await expect(page.getByText("Teşekkürler")).toBeVisible();
  expect(sent).toEqual({ code: BASE.access_code, helpful: true });
});

test("my tickets shows the staff reply for a ticket sent from this browser", async ({ page }) => {
  await page.route("**/api/tickets/lookup", (route) =>
    route.fulfill({
      json: {
        ticket_id: 42,
        status: "handled",
        office: "student_affairs",
        reply: "Dilekçe verin.",
        handled_at: null,
      },
    }),
  );
  await askWithAnswer(page, {});
  await expect(page.getByText("Talep no #42")).toBeVisible(); // the answer arrived: ticket remembered
  await page.goto("/my-tickets");
  await expect(page.getByText("#42")).toBeVisible();
  await expect(page.getByText("Dilekçe verin.")).toBeVisible();
});
