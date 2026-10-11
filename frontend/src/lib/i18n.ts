// Every text the student sees, in Turkish and English. The `satisfies` check makes
// TypeScript fail the build if a key exists in one language but not the other.

import type { Category, Language, Priority } from "@/lib/types";

const tr = {
  university: "Bilecik Şeyh Edebali Üniversitesi",
  title: "Öğrenci Yardım Masası",
  welcomeTitle: "Size nasıl yardımcı olabiliriz?",
  welcomeText:
    "Sorunuzu yazın. Cevabı resmî BŞEÜ belgelerinde ararız; bulamazsak talebinizi doğru birime iletiriz.",
  examples: [
    "Final sınavına giremedim, ne yapmalıyım?",
    "Kaydımı sildirirsem harç iade edilir mi?",
    "Yaz okulunda en fazla kaç ders alabilirim?",
    "OBS şifremi unuttum, nasıl sıfırlarım?",
  ],
  placeholder: "Sorununuzu yazın…",
  send: "Gönder",
  disclaimer: "Yapay zekâ hata yapabilir. Resmî kararları her zaman ilgili birim verir.",
  steps: ["Talebiniz okunuyor", "Resmî belgelerde aranıyor", "Cevap hazırlanıyor"],
  answered: "Resmî belgelere dayanarak yanıtlandı",
  forwarded: "İlgili birime iletildi",
  forwardedText:
    "Bu konuda kesin bir cevabı yalnızca bir personel verebilir. Talebiniz ve yapay zekânın hazırladığı taslak, aşağıdaki birime iletildi.",
  nextStep: "Bir personel talebinizi inceleyip size dönüş yapacak.",
  emergency: "Acil bir tehlike varsa hemen 112'yi arayın.",
  sources: "Kaynaklar",
  ticketNo: "Talep no",
  office: "Birim",
  helpful: "Bu cevap işinize yaradı mı?",
  newChat: "Yeni talep",
  error: "Şu anda cevap veremiyoruz. Lütfen biraz sonra tekrar deneyin.",
  theme: { light: "Açık", dark: "Koyu", system: "Sistem" },
  categories: {
    account_access: "Hesap Erişimi",
    it_support: "Teknik Destek",
    registration: "Ders Kaydı",
    academic_records: "Akademik Kayıtlar",
    billing: "Harç ve Ödemeler",
    campus_life: "Kampüs Yaşamı",
    other: "Diğer",
  } satisfies Record<Category, string>,
  priorities: {
    urgent: "Acil",
    high: "Yüksek",
    medium: "Orta",
    low: "Düşük",
  } satisfies Record<Priority, string>,
};

export type Texts = typeof tr;

const en: Texts = {
  university: "Bilecik Şeyh Edebali University",
  title: "Student Helpdesk",
  welcomeTitle: "How can we help you?",
  welcomeText:
    "Write your question. We look for the answer in official BŞEÜ documents; if we can't find it, we forward your request to the right office.",
  examples: [
    "I missed my final exam, what can I do?",
    "If I withdraw, do I get my tuition back?",
    "How many courses can I take in summer school?",
    "I forgot my OBS password, how do I reset it?",
  ],
  placeholder: "Describe your problem…",
  send: "Send",
  disclaimer: "AI can make mistakes. Official decisions are always made by the responsible office.",
  steps: ["Reading your request", "Searching official documents", "Writing the answer"],
  answered: "Answered from official documents",
  forwarded: "Forwarded to the right office",
  forwardedText:
    "Only a staff member can give a definite answer here. Your request and the AI's draft were sent to the office below.",
  nextStep: "A staff member will review your request and get back to you.",
  emergency: "If you are in immediate danger, call 112 now.",
  sources: "Sources",
  ticketNo: "Ticket no",
  office: "Office",
  helpful: "Was this answer helpful?",
  newChat: "New request",
  error: "We can't answer right now. Please try again in a moment.",
  theme: { light: "Light", dark: "Dark", system: "System" },
  categories: {
    account_access: "Account access",
    it_support: "IT support",
    registration: "Course registration",
    academic_records: "Academic records",
    billing: "Fees and payments",
    campus_life: "Campus life",
    other: "Other",
  },
  priorities: { urgent: "Urgent", high: "High", medium: "Medium", low: "Low" },
};

export const TEXTS: Record<Language, Texts> = { tr, en };
