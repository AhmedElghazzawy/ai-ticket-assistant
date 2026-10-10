// The student chat page: sends questions to POST /api/tickets and shows the answers.
// Safety rule: every text from the student or the AI is inserted with textContent, never innerHTML,
// so it is always shown as plain text and can never run as code on the page (XSS).

const TEXTS = {
  tr: {
    title: "Öğrenci Yardım Masası",
    tagline: "Yapay zekâ destekli asistan · prototip",
    eyebrow: "Bilecik Şeyh Edebali Üniversitesi",
    welcome_title: "Size nasıl yardımcı olabiliriz?",
    welcome_text: "Sorunuzu yazın. Cevabı resmî BŞEÜ belgelerinde ararız; bulamazsak talebinizi ilgili birime iletiriz.",
    examples: [["📝", "Final sınavına giremedim, ne yapmalıyım?"], ["💳", "Kaydımı sildirirsem harç iade edilir mi?"],
               ["☀️", "Yaz okulunda en fazla kaç ders alabilirim?"]],
    verified: "✓ Resmî BŞEÜ belgelerine dayanır",
    placeholder: "Sorununuzu yazın...",
    send: "Gönder",
    forwarded: "Talebiniz yukarıdaki birime iletildi; bir personel size dönüş yapacak.",
    emergency: "🚨 Acil bir tehlike varsa hemen 112'yi arayın.",
    source: "Kaynak",
    ticket_no: "Talep no",
    error: "Şu anda cevap veremiyoruz. Lütfen biraz sonra tekrar deneyin.",
    footer: "📞 Öğrenci İşleri Daire Başkanlığı · 0228 214 10 71 · ogrenciisleri@bilecik.edu.tr",
    categories: { account_access: "Hesap Erişimi", it_support: "Teknik Destek", registration: "Ders Kaydı",
                  academic_records: "Akademik Kayıtlar", billing: "Ödemeler", campus_life: "Kampüs Yaşamı", other: "Diğer" },
    priorities: { urgent: "Acil", high: "Yüksek", medium: "Orta", low: "Düşük" },
  },
  en: {
    title: "Student Helpdesk",
    tagline: "AI-assisted assistant · prototype",
    eyebrow: "Bilecik Şeyh Edebali University",
    welcome_title: "How can we help you?",
    welcome_text: "Write your question. We look for the answer in official BŞEÜ documents; if we can't find it, we forward your request to the right office.",
    examples: [["📝", "I missed my final exam, what can I do?"], ["💳", "If I withdraw, do I get my tuition back?"],
               ["☀️", "How many courses can I take in summer school?"]],
    verified: "✓ Based on official BŞEÜ documents",
    placeholder: "Describe your problem...",
    send: "Send",
    forwarded: "Your request has been forwarded to the office above; a staff member will get back to you.",
    emergency: "🚨 If you are in immediate danger, call 112 now.",
    source: "Source",
    ticket_no: "Ticket no",
    error: "We can't answer right now. Please try again in a moment.",
    footer: "📞 Student Affairs (Öğrenci İşleri) · 0228 214 10 71 · ogrenciisleri@bilecik.edu.tr",
    categories: { account_access: "Account access", it_support: "IT support", registration: "Course registration",
                  academic_records: "Academic records", billing: "Payments", campus_life: "Campus life", other: "Other" },
    priorities: { urgent: "Urgent", high: "High", medium: "Medium", low: "Low" },
  },
};

let lang = localStorage.getItem("lang") || "tr";
const form = document.getElementById("ask-form");
const input = document.getElementById("question");
const sendButton = document.getElementById("send");
const messages = document.getElementById("messages");
const themeToggle = document.getElementById("theme-toggle");

// Small helper: create an element with a class and SAFE text (textContent).
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// ---------- Language ----------
function applyLanguage() {
  const t = TEXTS[lang];
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = t[node.dataset.i18n]; });
  input.placeholder = t.placeholder;
  document.querySelectorAll("[data-lang]").forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));
  const buttons = t.examples.map(([icon, question]) => {
    const button = el("button", "example-card");
    button.type = "button";
    button.append(el("span", "icon", icon), el("span", "", question));
    button.onclick = () => ask(question);
    return button;
  });
  document.getElementById("examples").replaceChildren(...buttons);
}

document.querySelectorAll("[data-lang]").forEach((button) => {
  button.onclick = () => { lang = button.dataset.lang; localStorage.setItem("lang", lang); applyLanguage(); };
});

// ---------- Light / dark theme ----------
function currentTheme() {
  return document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function showThemeIcon() { themeToggle.textContent = currentTheme() === "dark" ? "☀️" : "🌙"; }
themeToggle.onclick = () => {
  const theme = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = theme;  // the CSS switches all colors from this one attribute
  localStorage.setItem("theme", theme);
  showThemeIcon();
};

// ---------- Chat ----------
// Each message sits in a row; the assistant's row starts with a small avatar.
function row(kind, bubble) {
  const line = el("div", "row " + kind);
  if (kind === "bot") line.append(el("div", "avatar", "AI"));
  line.append(bubble);
  return line;
}

function typingDots() {
  const box = el("div", "msg bot");
  const dots = el("span", "dots");
  dots.append(el("span"), el("span"), el("span"));
  box.append(dots);
  return row("bot", box);
}

function botMessage(data) {
  const t = TEXTS[lang];
  const box = el("div", "msg bot" + (data.auto_send ? "" : " forwarded"));
  const meta = el("div", "meta");
  meta.append(el("span", "chip", `${t.ticket_no} #${data.ticket_id}`), el("span", "chip", t.categories[data.category]),
              el("span", "chip " + data.priority, t.priorities[data.priority]));
  box.append(meta, el("div", "office", "🏢 " + data.office));
  if (data.auto_send) {  // every safety check passed on the server: show the cited answer
    box.append(el("div", "", data.reply), el("div", "verified", t.verified));
    data.sources.forEach((s) => box.append(el("div", "source", `📄 ${t.source}: ${s.title} · ${s.section}`)));
  } else {  // a human will answer
    box.append(el("div", "", t.forwarded));
  }
  if (data.emergency) box.append(el("div", "emergency", t.emergency));
  return box;
}

function setBusy(busy) { sendButton.disabled = busy; input.disabled = busy; }

async function ask(text) {
  text = text.trim();
  if (!text) return;
  document.getElementById("welcome").hidden = true;
  messages.append(row("user", el("div", "msg user", text)));
  const typing = typingDots();
  messages.append(typing);
  typing.scrollIntoView({ behavior: "smooth" });
  setBusy(true);
  try {
    const response = await fetch("/api/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: lang }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    typing.replaceWith(row("bot", botMessage(await response.json())));
  } catch {
    typing.replaceWith(row("bot", el("div", "msg bot forwarded", TEXTS[lang].error)));
  }
  setBusy(false);
  messages.lastElementChild.scrollIntoView({ behavior: "smooth" });
  input.focus();
}

form.onsubmit = (event) => {
  event.preventDefault();  // stay on the page instead of reloading it
  const text = input.value;
  input.value = "";
  input.style.height = "auto";
  ask(text);
};
input.addEventListener("keydown", (event) => {  // Enter sends, Shift+Enter makes a new line
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
});
input.addEventListener("input", () => {  // the box grows with the text
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
});

// ---------- Start ----------
const savedTheme = localStorage.getItem("theme");
if (savedTheme) document.documentElement.dataset.theme = savedTheme;
showThemeIcon();
applyLanguage();
