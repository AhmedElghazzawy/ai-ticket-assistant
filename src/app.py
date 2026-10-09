"""Web page for the ticket assistant. Run with: .venv/bin/streamlit run src/app.py"""

import json
from pathlib import Path

import streamlit as st

from decision import UNITS
from llm import MODEL
from pipeline import process_ticket
from retrieval import load_index
from tickets import TEST_PATH, TICKETS_PATH, Ticket, load_tickets

# Every text on the page, in both languages. Add new texts to both.
TEXTS = {
    "tr": {
        "title": "🎓 BŞEÜ Öğrenci Yardım Masası",
        "tagline": "Yapay zekâ destekli yardım asistanı · prototip",
        "subtitle": "BŞEÜ öğrenci ticket'larını okur, etiketler ve taslak cevap yazar.",
        "about": "Çalışma Tasarımı I projesi. Ticket → sınıflandırma → belge arama (RAG) → kaynaklı cevap → otomatik gönder veya birime yönlendir.",
        "progress": "📊 Proje durumu",
        "menu": "Menü",
        "steps": ["Gemini bağlantısı", "Etiket kuralları", "80 ticket'lık veri seti", "Sınıflandırma",
                  "Değerlendirme (skor)", "Belge arama (RAG)", "Karar ve yönlendirme"],
        "model": "Model",
        "view": "Görünüm",
        "student_view": "🎓 Öğrenci",
        "staff_view": "🛠 Personel",
        "greeting": "Merhaba! BŞEÜ Öğrenci Yardım Masası'na hoş geldiniz. Sorununuzu kısaca yazın, ilgili birime iletelim.",
        "chat_box": "Sorununuzu yazın...",
        "received": "Talebiniz alındı.",
        "topic": "Konu",
        "unit": "İlgili birim",
        "forwarded": "Talebiniz yukarıdaki birime iletildi; bir personel size dönüş yapacak.",
        "emergency": "Acil bir tehlike varsa hemen 112'yi arayın.",
        "clear": "Sohbeti temizle",
        "try_examples": "Örnek sorular:",
        "footer": "Öğrenci İşleri Daire Başkanlığı · 0228 214 10 71 · ogrenciisleri@bilecik.edu.tr",
        "examples": ["Final sınavına giremedim, ne yapmalıyım?", "Kaydımı sildirirsem harç iade edilir mi?",
                     "Yaz okulunda en fazla kaç ders alabilirim?"],
        "source_label": "Kaynak",
        "demo_note": "Prototip: cevaplar yalnızca resmî BŞEÜ belgelerine dayanır; belgeler sorunuzu yanıtlamıyorsa talebiniz ilgili birime iletilir.",
        "tab_overview": "🏠 Genel bakış",
        "pipeline": "Sistem nasıl çalışır",
        "key_results": "Temel sonuçlar",
        "test_score": "Test skoru (üçü de doğru)",
        "missed_test": "Kaçırılan escalation (test)",
        "hit3": "Doğru belge ilk 3'te (test)",
        "unsafe": "Hatalı otomatik gönderim (dev)",
        "not_run": "henüz çalıştırılmadı",
        "units_table": "Kategoriler ve birimler",
        "office": "Birim",
        "nodes": ["Öğrenci ticket'ı", "Sınıflandırma", "Belge arama (RAG)", "Kaynaklı cevap", "Karar", "Otomatik gönder", "Birime yönlendir"],
        "tab_try": "💬 Ticket dene",
        "tab_data": "📋 Veri seti",
        "tab_eval": "📊 Değerlendirme",
        "no_results": "Henüz sonuç yok. Terminalde çalıştırın:",
        "results_file": "Sonuç dosyası",
        "run_info": "Model {model}, düşünme seviyesi {level}, {runs} çalıştırma, {date}",
        "score_table": "Skorlar (1. çalıştırma)",
        "metric": "Ölçüt",
        "all_three": "Üçü de doğru",
        "within_one": "Öncelik (bir seviye yakın)",
        "missed": "Kaçırılan escalation",
        "missed_help": "İnsana gitmesi gerekip gitmeyen ticket'lar: en tehlikeli hata.",
        "over": "Gereksiz escalation",
        "consistency": "Tutarlılık (1. ve 2. çalıştırma aynı etiket)",
        "mistakes": "Hatalar (1. çalıştırma) ve modelin gerekçesi",
        "mine": "benim",
        "model_says": "model",
        "rerun": "Yeni bir değerlendirme yaklaşık 20 dakika ve 160 API çağrısı sürer. Terminalde çalıştırın:",
        "limits": "Bu skor ne kanıtlamaz: kural kitabı bu 80 ticket'a bakılarak düzeltildi, bu yüzden skor iyimserdir. Güvenilir skor Phase 2'deki kilitli test setinden gelecek. Etiketler de tartışmalı olabilir ve ticket'ları biz yazdık.",
        "ticket_box": "Öğrencinin ticket'ı",
        "example": "Veri setinden örnek seç",
        "example_hint": "Bir örnek seçin veya kendiniz yazın",
        "send": "Gönder",
        "empty": "Lütfen bir ticket yazın.",
        "thinking": "Model düşünüyor...",
        "reply": "Taslak cevap",
        "reply_language": "Turkish",
        "reply_hint": "Bir ticket yazıp Gönder'e basın.",
        "labels": "Etiketler",
        "reason": "Modelin gerekçesi",
        "esc_yes": "🙋 İnsana yönlendir",
        "esc_no": "Escalation gerekmiyor",
        "retrieved": "Bulunan kurallar (benzerlik puanı)",
        "evidence": "Kanıt (kurallardan alıntı)",
        "covered": "Belgeler cevaplıyor mu",
        "decision": "Karar",
        "auto_yes": "✅ Otomatik gönderilir",
        "auto_no": "🙋 Birime yönlendirilir",
        "no_data": "Henüz ticket yok. data/tickets/tickets.jsonl dosyasını oluşturun.",
        "count": "Ticket sayısı",
        "filter": "Dil",
        "all": "Hepsi",
        "category": "Kategori",
        "priority": "Öncelik",
        "escalate": "Escalation",
        "yes": "Evet",
        "no": "Hayır",
        "search": "Metinde ara",
        "escalate_rate": "Escalation oranı",
        "text_col": "Ticket metni",
    },
    "en": {
        "title": "🎓 BŞEÜ Student Helpdesk",
        "tagline": "AI-assisted helpdesk assistant · prototype",
        "subtitle": "Reads BŞEÜ student tickets, labels them and drafts a reply.",
        "about": "Çalışma Tasarımı I project. Ticket → classification → document search (RAG) → reply with source → auto-send or route to an office.",
        "progress": "📊 Project status",
        "menu": "Menu",
        "steps": ["Gemini connection", "Label rules", "80-ticket dataset", "Classification",
                  "Evaluation (score)", "Document search (RAG)", "Decision and routing"],
        "model": "Model",
        "view": "View",
        "student_view": "🎓 Student",
        "staff_view": "🛠 Staff",
        "greeting": "Hello! Welcome to the BŞEÜ Student Helpdesk. Briefly describe your problem and we will pass it to the right office.",
        "chat_box": "Describe your problem...",
        "received": "Your request has been received.",
        "topic": "Topic",
        "unit": "Responsible office",
        "forwarded": "Your request has been forwarded to the office above; a staff member will get back to you.",
        "emergency": "If you are in immediate danger, call 112 now.",
        "clear": "Clear chat",
        "try_examples": "Example questions:",
        "footer": "Student Affairs (Öğrenci İşleri) · 0228 214 10 71 · ogrenciisleri@bilecik.edu.tr",
        "examples": ["I missed my final exam, what can I do?", "If I withdraw, do I get my tuition back?",
                     "How many courses can I take in summer school?"],
        "source_label": "Source",
        "demo_note": "Prototype: answers come only from official BŞEÜ documents; if they do not answer your question, your request is forwarded to the responsible office.",
        "tab_overview": "🏠 Overview",
        "pipeline": "How the system works",
        "key_results": "Key results",
        "test_score": "Test score (all three correct)",
        "missed_test": "Missed escalations (test)",
        "hit3": "Right document in top 3 (test)",
        "unsafe": "Unsafe auto-sends (dev)",
        "not_run": "not run yet",
        "units_table": "Categories and offices",
        "office": "Office",
        "nodes": ["Student ticket", "Classification", "Document search (RAG)", "Cited answer", "Decision", "Auto-send", "Route to office"],
        "tab_try": "💬 Try a ticket",
        "tab_data": "📋 Dataset",
        "tab_eval": "📊 Evaluation",
        "no_results": "No results yet. Run in the terminal:",
        "results_file": "Results file",
        "run_info": "Model {model}, thinking level {level}, {runs} runs, {date}",
        "score_table": "Scores (run 1)",
        "metric": "Metric",
        "all_three": "All three correct",
        "within_one": "Priority (within one level)",
        "missed": "Missed escalations",
        "missed_help": "Tickets that needed a human but were not escalated: the most dangerous error.",
        "over": "Over-escalations",
        "consistency": "Consistency (same label in run 1 and run 2)",
        "mistakes": "Mistakes (run 1) and the model's reason",
        "mine": "mine",
        "model_says": "model",
        "rerun": "A new evaluation takes about 20 minutes and 160 API calls. Run it in the terminal:",
        "limits": "What this score does NOT prove: the rulebook was fixed while looking at these 80 tickets, so the score is optimistic. The trustworthy score comes from the locked test set in Phase 2. Labels can be debatable, and we wrote the tickets ourselves.",
        "ticket_box": "The student's ticket",
        "example": "Pick an example from the dataset",
        "example_hint": "Pick an example or write your own",
        "send": "Send",
        "empty": "Please write a ticket.",
        "thinking": "The model is thinking...",
        "reply": "Draft reply",
        "reply_language": "English",
        "reply_hint": "Write a ticket and press Send.",
        "labels": "Labels",
        "reason": "The model's reason",
        "esc_yes": "🙋 Send to a human",
        "esc_no": "No escalation needed",
        "retrieved": "Retrieved rules (similarity score)",
        "evidence": "Evidence (quoted from the rules)",
        "covered": "Covered by the documents",
        "decision": "Decision",
        "auto_yes": "✅ Auto-send",
        "auto_no": "🙋 Route to the office",
        "no_data": "No tickets yet. Create data/tickets/tickets.jsonl.",
        "count": "Number of tickets",
        "filter": "Language",
        "all": "All",
        "category": "Category",
        "priority": "Priority",
        "escalate": "Escalation",
        "yes": "Yes",
        "no": "No",
        "search": "Search in text",
        "escalate_rate": "Escalation rate",
        "text_col": "Ticket text",
    },
}
DONE_STEPS = 7  # how many of the steps above are finished; raise it as the project grows

# Readable names for the label IDs (the IDs themselves stay English in the data).
CATEGORY_NAMES = {
    "tr": {"account_access": "Hesap Erişimi", "it_support": "Teknik Destek", "registration": "Ders Kaydı",
           "academic_records": "Akademik Kayıtlar", "billing": "Ödemeler", "campus_life": "Kampüs Yaşamı",
           "other": "Diğer"},
    "en": {"account_access": "Account access", "it_support": "IT support", "registration": "Course registration",
           "academic_records": "Academic records", "billing": "Payments", "campus_life": "Campus life",
           "other": "Other"},
}
PRIORITY_NAMES = {
    "tr": {"urgent": "🔴 Acil", "high": "🟠 Yüksek", "medium": "🟡 Orta", "low": "🟢 Düşük"},
    "en": {"urgent": "🔴 Urgent", "high": "🟠 High", "medium": "🟡 Medium", "low": "🟢 Low"},
}


@st.cache_resource
def get_index() -> list:
    """Load the saved knowledge-base vectors once per server, not on every click."""
    return load_index()


def student_answer(ticket: str, t: dict, language: str) -> str:
    """Run the whole pipeline and build the chat answer: topic, office, then the cited reply or a hand-off."""
    r = process_ticket(ticket, language, get_index())
    c = r.classification
    lines = [
        f"✅ {t['received']}",
        f"📌 **{t['topic']}:** {CATEGORY_NAMES[language][c.category]} · "
        f"**{t['priority']}:** {PRIORITY_NAMES[language][c.priority]}",
        f"🏢 **{t['unit']}:** {UNITS[language][c.category]}",
    ]
    if r.decision.auto_send:  # every safety check passed: send the grounded, cited reply
        lines.append(f"💬 {r.answer.reply}")
        cited = {chunk.id: chunk for _, chunk in r.hits}
        for source_id in r.answer.sources:  # the exact section and article, e.g. "Mazeret sınavı (Madde 21)"
            chunk = cited[source_id]
            lines.append(f"> 📄 **{t['source_label']}:** {chunk.title} · {chunk.text.splitlines()[0]}")
    else:  # a human answers; the student never sees an unchecked AI reply
        lines.append(f"🙋 {t['forwarded']}")
        if c.escalate and c.priority == "urgent":
            lines.append(f"🚨 **{t['emergency']}**")
    return "\n\n".join(lines)


RESULTS_DIR = Path(__file__).resolve().parent.parent / "eval"


def banner(title: str, tagline: str) -> str:
    """BŞEÜ-style header with the university's own red gradient (bilecik.edu.tr tema-default.css).

    HTML only for our fixed texts; user input must never be put into HTML.
    """
    return ("<div style='background: linear-gradient(90deg, #943434 0%, #DC4C2D 100%); color: #ffffff; "
            "padding: 1.1rem 1.5rem; border-radius: 0.75rem; margin-bottom: 0.5rem'>"
            f"<div style='font-size: 1.7rem; font-weight: 700'>{title}</div>"
            f"<div style='opacity: 0.9'>{tagline}</div></div>")


def read_json(name: str) -> dict | None:
    """One saved results file from eval/, or None if that evaluation has not been run yet."""
    path = RESULTS_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def read_results() -> dict[str, dict]:
    """All saved evaluation runs, keyed by file name (e.g. results_high.json)."""
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(RESULTS_DIR.glob("results_*.json"))}


def read_dataset() -> tuple[list[Ticket], str | None]:
    """Load the tickets once for both tabs. Return an error message instead of crashing."""
    if not TICKETS_PATH.exists():
        return [], None
    try:
        return load_tickets(), None
    except ValueError as error:
        return [], str(error)


# The sidebar starts closed: the main page shows only the chat; everything else opens on click.
st.set_page_config(page_title="BŞEÜ Yardım Masası", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

title_col, language_col = st.columns([6, 1], vertical_alignment="center")
language = language_col.radio("Dil / Language", ["tr", "en"], format_func=str.upper, horizontal=True,
                              label_visibility="collapsed")
t = TEXTS[language]  # t["title"] gives the title in the chosen language
title_col.markdown(banner(t["title"], t["tagline"]), unsafe_allow_html=True)

with st.sidebar:
    st.subheader(t["menu"])
    view = st.radio(t["view"], ["student", "staff"], format_func=lambda v: t[f"{v}_view"])
    with st.expander(t["progress"]):  # closed until clicked
        st.caption(t["about"])
        for number, step in enumerate(t["steps"]):
            st.markdown(("✅ " if number < DONE_STEPS else "⏳ ") + step)
        st.caption(t["demo_note"])
        st.caption(f"{t['model']}: `{MODEL}`")

if view == "student":
    if "messages" not in st.session_state:
        st.session_state.messages = []  # the chat history, kept between reruns
    if not st.session_state.messages:  # welcome card, only before the conversation starts
        _, middle, _ = st.columns([1, 3, 1])
        with middle.container(border=True):
            # HTML only to center OUR fixed text; never put user input into HTML.
            st.markdown(f"<div style='text-align:center; padding:1rem'>"
                        f"<div style='font-size:2.5rem'>🎓</div><p>{t['greeting']}</p></div>",
                        unsafe_allow_html=True)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    picked = None
    if not st.session_state.messages:
        st.caption(t["try_examples"])
        for column, example in zip(st.columns(len(t["examples"])), t["examples"]):
            if column.button(example):
                picked = example
    st.caption(f"📞 {t['footer']}")  # the real office, as a fallback for anything the chat cannot solve
    if question := st.chat_input(t["chat_box"]) or picked:  # := stores the text and checks it is not empty
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            try:
                with st.spinner(t["thinking"]):
                    answer = student_answer(question, t, language)
            except Exception as error:  # noqa: BLE001 - show the problem in the chat instead of crashing
                answer = f"⚠️ {type(error).__name__}: {error}"
            st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
    if st.session_state.messages and st.sidebar.button(t["clear"]):
        st.session_state.messages = []
        st.rerun()
    st.stop()  # the staff view below is not drawn

tickets, data_error = read_dataset()

st.caption(t["subtitle"])
tab_overview, tab_try, tab_data, tab_eval = st.tabs([t["tab_overview"], t["tab_try"], t["tab_data"], t["tab_eval"]])

with tab_overview:
    st.subheader(t["pipeline"])
    n = t["nodes"]  # ticket, classify, search, answer, decision, auto-send, route
    st.graphviz_chart(f"""digraph {{ rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#f6e3e3", color="#a90005"];
        "{n[0]}" -> "{n[1]}" -> "{n[2]}" -> "{n[3]}" -> "{n[4]}";
        "{n[4]}" -> "{n[5]}" [label="✓"]; "{n[4]}" -> "{n[6]}" [label="✗"]; }}""")

    st.subheader(t["key_results"])
    test, retrieval, pipeline_dev = read_json("results_high_test.json"), read_json("retrieval_results.json"), read_json("pipeline_results_dev.json")
    k1, k2, k3, k4 = st.columns(4)
    runs = [test[key] for key in ("score_run1", "score_run2") if test and test.get(key)]  # average both runs
    k1.metric(t["test_score"], f"{sum(r['all_three'] for r in runs) / len(runs):.1%}" if runs else t["not_run"])
    k2.metric(t["missed_test"], len(test["score_run1"]["missed_escalations"]) if test else t["not_run"])
    k3.metric(t["hit3"], f"{retrieval['test']['summary']['hit@3']:.0%}" if retrieval else t["not_run"])
    k4.metric(t["unsafe"], len(pipeline_dev["summary"]["unsafe_auto_sends"]) if pipeline_dev else t["not_run"])

    st.subheader(t["units_table"])
    st.dataframe([{t["category"]: CATEGORY_NAMES[language][cat], t["office"]: UNITS[language][cat]}
                  for cat in CATEGORY_NAMES[language]], hide_index=True)

def use_example(examples: dict[str, str]) -> None:
    """Copy the chosen example ticket into the text box."""
    chosen = st.session_state.example
    if chosen:
        st.session_state.ticket = examples[chosen]


with tab_try:
    left, right = st.columns(2, gap="large")
    with left:
        examples = {x.id: x.text for x in tickets if x.language == language}  # id -> text
        st.selectbox(
            t["example"], list(examples), index=None, placeholder=t["example_hint"],
            format_func=lambda ticket_id: f"{ticket_id} · {examples[ticket_id][:70]}",
            key="example", on_change=use_example, args=(examples,),
        )
        ticket = st.text_area(t["ticket_box"], height=150, key="ticket")
        send = st.button(t["send"], type="primary")

    with right:
        if send and not ticket.strip():
            st.warning(t["empty"])
        elif send:
            try:
                with st.spinner(t["thinking"]):
                    r = process_ticket(ticket, language, get_index())
                c = r.classification
                st.subheader(t["labels"])
                c1, c2, c3 = st.columns(3)
                c1.metric(t["category"], CATEGORY_NAMES[language][c.category])
                c2.metric(t["priority"], PRIORITY_NAMES[language][c.priority])
                c3.metric(t["escalate"], t["esc_yes"] if c.escalate else t["esc_no"])
                st.caption(f"**{t['reason']}:** {c.reason}")
                st.subheader(t["retrieved"])
                for score, chunk in r.hits:
                    st.markdown(f"- `{score:.3f}` **{chunk.id}**: {chunk.text.splitlines()[0]}")
                st.subheader(t["reply"])
                st.caption(f"**{t['covered']}:** {r.answer.covered} · **{t['evidence']}:** {r.answer.evidence or '-'}")
                with st.container(border=True):
                    st.markdown(r.answer.reply)
                st.subheader(t["decision"])
                if r.decision.auto_send:
                    st.success(t["auto_yes"])
                else:
                    st.warning(f"{t['auto_no']}: {UNITS[language][c.category]}")
                    for reason in r.decision.reasons:
                        st.markdown(f"- {reason}")
            except Exception as error:  # noqa: BLE001 - on purpose: show any problem on the page, not a crash
                st.error(f"{type(error).__name__}: {error}")
        else:
            st.caption(t["reply_hint"])

with tab_data:
    if data_error:  # a bad line in tickets.jsonl: show which one, like the terminal does
        st.error(data_error)
    elif not tickets:
        st.info(t["no_data"])
    else:
        names, prio_names = CATEGORY_NAMES[language], PRIORITY_NAMES[language]

        # Filters: an empty choice means "show all".
        search_col, lang_col = st.columns([3, 1])
        search = search_col.text_input(t["search"])
        lang_choice = lang_col.radio(t["filter"], [t["all"], "tr", "en"], horizontal=True)
        cat_col, prio_col, esc_col = st.columns(3)
        cats = cat_col.multiselect(t["category"], list(names), format_func=names.get, placeholder=t["all"])
        prios = prio_col.multiselect(t["priority"], list(prio_names), format_func=prio_names.get, placeholder=t["all"])
        esc_choice = esc_col.selectbox(t["escalate"], [t["all"], t["yes"], t["no"]])

        shown = [x for x in tickets if search.lower() in x.text.lower()]
        if lang_choice != t["all"]:
            shown = [x for x in shown if x.language == lang_choice]
        if cats:
            shown = [x for x in shown if x.category in cats]
        if prios:
            shown = [x for x in shown if x.priority in prios]
        if esc_choice != t["all"]:
            shown = [x for x in shown if x.escalate == (esc_choice == t["yes"])]

        # Summary numbers for the tickets currently shown.
        escalated = sum(x.escalate for x in shown)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t["count"], len(shown))
        m2.metric("TR", sum(x.language == "tr" for x in shown))
        m3.metric("EN", sum(x.language == "en" for x in shown))
        m4.metric(t["escalate_rate"], f"{escalated / len(shown):.0%}" if shown else "–")

        rows = [
            {"id": x.id, "category": names[x.category], "priority": prio_names[x.priority],
             "escalate": x.escalate, "text": x.text}
            for x in shown
        ]
        st.dataframe(rows, hide_index=True, column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "category": st.column_config.TextColumn(t["category"]),
            "priority": st.column_config.TextColumn(t["priority"]),
            "escalate": st.column_config.CheckboxColumn(t["escalate"], width="small"),
            "text": st.column_config.TextColumn(t["text_col"], width="large"),
        })

with tab_eval:
    all_results = read_results()
    if not all_results:
        st.info(t["no_results"])
        st.code(".venv/bin/python src/evaluate.py high")
    else:
        newest = max(all_results, key=lambda name: all_results[name]["date"])  # open the latest run first
        chosen = st.radio(t["results_file"], list(all_results), index=list(all_results).index(newest), horizontal=True)
        res = all_results[chosen]
        st.caption(t["run_info"].format(model=res["model"], level=res["thinking_level"], runs=res["runs"], date=res["date"])
                   + f" · {res.get('dataset', 'dev')}")

        # Scores table: one row per metric, one column per language group.
        names = {"category": t["category"], "priority": t["priority"], "escalate": t["escalate"],
                 "all_three": t["all_three"], "priority_within_one": t["within_one"]}
        groups = {t["all"]: res["score_run1"], "TR": res["score_run1_tr"], "EN": res["score_run1_en"]}
        st.subheader(t["score_table"])
        st.dataframe(
            [{t["metric"]: label, **{g: f"{s[key]:.1%}" for g, s in groups.items()}} for key, label in names.items()],
            hide_index=True,
        )

        run1 = res["score_run1"]
        col_missed, col_over = st.columns(2)
        col_missed.metric(t["missed"], len(run1["missed_escalations"]), help=t["missed_help"])
        col_missed.caption(", ".join(run1["missed_escalations"]) or "✅")
        col_over.metric(t["over"], len(run1["over_escalations"]))
        col_over.caption(", ".join(run1["over_escalations"]) or "✅")

        if res["consistency"]:
            c = res["consistency"]
            st.subheader(t["consistency"])
            k1, k2, k3 = st.columns(3)
            k1.metric(t["category"], f"{c['category']:.0%}")
            k2.metric(t["priority"], f"{c['priority']:.0%}")
            k3.metric(t["escalate"], f"{c['escalate']:.0%}")

        # Every run-1 mistake, side by side with my label and the model's reason.
        st.subheader(t["mistakes"])
        first_run = res["predictions"][0]
        scored = load_tickets(TEST_PATH) if res.get("dataset") == "test" else tickets  # match the run's dataset
        rows = []
        for x in scored:
            p = first_run.get(x.id)
            wrong = [f for f in ("category", "priority", "escalate") if p and p[f] != getattr(x, f)]
            if wrong:
                diffs = "; ".join(f"{f}: {t['model_says']}={p[f]}, {t['mine']}={getattr(x, f)}" for f in wrong)
                rows.append({"id": x.id, "diff": diffs, "text": x.text, "reason": p["reason"]})
        st.dataframe(rows, hide_index=True, column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "diff": st.column_config.TextColumn(t["metric"], width="medium"),
            "text": st.column_config.TextColumn(t["text_col"], width="medium"),
            "reason": st.column_config.TextColumn(t["reason"], width="large"),
        })

        st.warning(t["limits"])
        st.caption(t["rerun"])
        st.code(".venv/bin/python src/evaluate.py high")
