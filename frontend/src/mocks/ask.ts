// A fake POST /api/tickets for the design prototype. The replies are REAL answers our
// pipeline produced (eval/pipeline_results_dev.json: tr-023, en-020) and the offices come
// from src/decision.py. Removed when the page is connected to the real API.

import type { Language, TicketOut } from "@/lib/types";

const GAZETTE = "https://www.resmigazete.gov.tr/eskiler/2019/07/20190707-1.htm";
const FEES_FAQ = "https://bilecik.edu.tr/ogrenciisleri/Icerik/HARc_isLEMLERi";

const REFUND_TR: TicketOut = {
  ticket_id: 128,
  category: "billing",
  priority: "medium",
  office: "Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü",
  auto_send: true,
  reply:
    "Merhaba. Üniversitemiz kurallarına göre, kayıt yaptırıp kendi isteği ile kaydını sildiren öğrencilerin katkı payı ve öğrenim ücretleri geri ödenmemektedir. Bu nedenle bu dönem ödediğiniz harcın iadesini almanız mümkün değildir.",
  sources: [
    {
      title: "Öğrenci İşleri Sıkça Sorulan Sorular: Harç İşlemleri",
      section: "Kayıt sildirince iade",
      url: FEES_FAQ,
    },
  ],
  emergency: false,
};

const MAKEUP_EN: TicketOut = {
  ticket_id: 129,
  category: "academic_records",
  priority: "medium",
  office: "Student Affairs (Öğrenci İşleri)",
  auto_send: true,
  reply:
    "There is no excused (mazeret) exam for a missed final, so your medical report cannot be used for a separate exam. However, students who met the attendance conditions but could not take the final automatically get a make-up exam (bütünleme) for each failed course, with no application needed.",
  sources: [
    { title: "BŞEÜ Undergraduate Regulation", section: "Excused exams (Article 21)", url: GAZETTE },
    { title: "BŞEÜ Undergraduate Regulation", section: "Make-up exam (Article 19)", url: GAZETTE },
  ],
  emergency: false,
};

const FORWARDED: Record<Language, TicketOut> = {
  tr: {
    ticket_id: 130,
    category: "academic_records",
    priority: "high",
    office: "Öğrenci İşleri Daire Başkanlığı",
    auto_send: false,
    reply: null,
    sources: [],
    emergency: false,
  },
  en: {
    ticket_id: 130,
    category: "academic_records",
    priority: "high",
    office: "Student Affairs (Öğrenci İşleri)",
    auto_send: false,
    reply: null,
    sources: [],
    emergency: false,
  },
};

/** Picks a realistic answer for the prototype. Only real replies are shown, so each language
 * has one answered example (TR: fee refund, EN: missed final); everything else is forwarded. */
export async function mockAsk(text: string, language: Language): Promise<TicketOut> {
  await new Promise((resolve) => setTimeout(resolve, 2400)); // like the real pipeline: a few seconds
  const lower = text.toLocaleLowerCase(language);
  if (language === "tr" && /harç|iade/.test(lower)) return REFUND_TR;
  if (language === "en" && /final|exam|make-up/.test(lower)) return MAKEUP_EN;
  return FORWARDED[language];
}
