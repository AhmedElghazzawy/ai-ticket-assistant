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
  general_help: null,
  emergency: false,
  access_code: "secret-code-1234567890",
  reasons: [],
  top_score: 0.78,
  min_score: 0.65,
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

test("a forwarded ticket with first help shows the cited part first", async ({ page }) => {
  await askWithAnswer(page, {
    first_help: true,
    reply: "Program OBS'de ilan edilir.",
    sources: [SOURCE],
  });
  await expect(page.getByText("Resmî belgelere göre")).toBeVisible();
  await expect(page.getByText("Program OBS'de ilan edilir.")).toBeVisible();
  await expect(page.getByText("Talebiniz ayrıca ilgili birime iletildi")).toBeVisible();
});

test("general help is shown labeled as not official", async ({ page }) => {
  await askWithAnswer(page, { general_help: "Kartı temizleyip tekrar deneyin." });
  await expect(page.getByText("Kartı temizleyip tekrar deneyin.")).toBeVisible();
  await expect(page.getByText("Genel bilgi", { exact: true })).toBeVisible();
  await expect(page.getByText("resmî belgelerinden değil")).toBeVisible();
  await expect(page.getByText("Resmî belgelere göre")).toHaveCount(0); // nothing cited
});

test("an urgent escalation shows the 112 line and no AI text", async ({ page }) => {
  await askWithAnswer(page, { priority: "urgent", emergency: true, office: "duty" });
  await expect(page.getByRole("link", { name: /112/ })).toHaveAttribute("href", "tel:112");
  await expect(page.getByText("Resmî belgelere göre")).toHaveCount(0);
  await expect(page.getByText("Genel bilgi", { exact: true })).toHaveCount(0);
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

test("the decision trace explains a forwarded ticket", async ({ page }) => {
  await askWithAnswer(page, {
    reasons: [{ code: "escalation" }],
    top_score: 0.81,
  });
  const trace = page.getByRole("button", { name: "Nasıl karar verildi?" });
  await expect(trace).toHaveAttribute("aria-expanded", "false");
  await trace.click();
  await expect(
    page.getByText("Bu konuda karar bir personele ait (yükseltme kuralı)."),
  ).toBeVisible();
  await expect(page.getByText("En iyi belge eşleşmesi 0.81 (eşik 0.65).")).toBeVisible();
  await expect(page.getByText("Talep, cevaplaması için ilgili birime iletildi.")).toBeVisible();
});

test("the live example can be asked for real", async ({ page }) => {
  let sent: unknown = null;
  await page.route("**/api/tickets", async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({
      json: { ...BASE, auto_send: true, reply: "Geri ödenmez.", sources: [SOURCE] },
    });
  });
  await page.goto("/");
  await expect(page.getByText("0/11")).toBeVisible(); // measured results on the start page
  await page.getByRole("button", { name: "Bu soruyu sor" }).click();
  await expect(page.getByText("Geri ödenmez.")).toBeVisible();
  expect(sent).toEqual({
    text: "Kaydımı sildirdim, bu dönem ödediğim harcın iadesini alabilir miyim?",
    language: "tr",
  });
});

for (const language of ["tr", "en"]) {
  test(`the start page fits the screen (${language})`, async ({ page }) => {
    // A long English source title once stretched a grid column: sideways scrolling on phones,
    // a squeezed results column on desktops.
    await page.addInitScript((lang) => localStorage.setItem("language", lang), language);
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    // The emulated screen width, not window.innerWidth: a phone browser widens that to fit the page.
    const screen = page.viewportSize()?.width ?? 0;
    const pageWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(pageWidth).toBeLessThanOrEqual(screen);
    if (screen >= 1024) {
      // Side by side on a wide screen: the results column must keep room for its numbers.
      const title = language === "tr" ? "Ölçülen sonuçlar" : "Measured results";
      const results = page.locator("section", { has: page.getByRole("heading", { name: title }) });
      expect((await results.boundingBox())?.width ?? 0).toBeGreaterThanOrEqual(250);
    }
  });
}
