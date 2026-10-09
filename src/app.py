"""Web page for the ticket assistant. Run with: .venv/bin/streamlit run src/app.py"""

import json
from pathlib import Path

import streamlit as st

from classifier import classify
from llm import MODEL, ask
from tickets import TICKETS_PATH, Ticket, load_tickets

# Every text on the page, in both languages. Add new texts to both.
TEXTS = {
    "tr": {
        "title": "🎓 Üniversite Yardım Masası Asistanı",
        "subtitle": "BŞEÜ öğrenci ticket'larını okur, etiketler ve taslak cevap yazar.",
        "about": "Çalışma Tasarımı I projesi. Ticket → sınıflandırma → belge arama (RAG) → kaynaklı cevap → otomatik gönder veya birime yönlendir.",
        "progress": "İlerleme",
        "steps": ["Gemini bağlantısı", "Etiket kuralları", "80 ticket'lık veri seti", "Sınıflandırma",
                  "Değerlendirme (skor)", "Belge arama (RAG)", "Karar ve yönlendirme"],
        "model": "Model",
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
        "draft_note": "Bu taslak henüz üniversite belgelerine dayanmıyor; gerçek bilgiler RAG ile (Phase 3) gelecek.",
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
        "title": "🎓 University Helpdesk Assistant",
        "subtitle": "Reads BŞEÜ student tickets, labels them and drafts a reply.",
        "about": "Çalışma Tasarımı I project. Ticket → classification → document search (RAG) → reply with source → auto-send or route to an office.",
        "progress": "Progress",
        "steps": ["Gemini connection", "Label rules", "80-ticket dataset", "Classification",
                  "Evaluation (score)", "Document search (RAG)", "Decision and routing"],
        "model": "Model",
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
        "draft_note": "This draft is not based on university documents yet; real facts come with RAG (Phase 3).",
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
DONE_STEPS = 5  # how many of the steps above are finished; raise it as the project grows

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


RESULTS_DIR = Path(__file__).resolve().parent.parent / "eval"


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


st.set_page_config(page_title="Helpdesk Assistant", page_icon="🎓", layout="wide")

with st.sidebar:
    language = st.radio("Dil / Language", ["tr", "en"], format_func=str.upper, horizontal=True)
    t = TEXTS[language]  # t["title"] gives the title in the chosen language
    st.caption(t["about"])
    st.subheader(t["progress"])
    for number, step in enumerate(t["steps"]):
        st.markdown(("✅ " if number < DONE_STEPS else "⏳ ") + step)
    st.caption(f"{t['model']}: `{MODEL}`")

tickets, data_error = read_dataset()

st.title(t["title"])
st.caption(t["subtitle"])
tab_try, tab_data, tab_eval = st.tabs([t["tab_try"], t["tab_data"], t["tab_eval"]])

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
            prompt = (
                "You are a university helpdesk assistant. "
                f"Reply briefly in {t['reply_language']} to this ticket:\n\n{ticket}"
            )
            try:
                with st.spinner(t["thinking"]):
                    result = classify(ticket)
                    reply = ask(prompt)
                st.subheader(t["labels"])
                c1, c2, c3 = st.columns(3)
                c1.metric(t["category"], CATEGORY_NAMES[language][result.category])
                c2.metric(t["priority"], PRIORITY_NAMES[language][result.priority])
                c3.metric(t["escalate"], t["esc_yes"] if result.escalate else t["esc_no"])
                st.caption(f"**{t['reason']}:** {result.reason}")
                st.subheader(t["reply"])
                with st.container(border=True):
                    st.markdown(reply)
                st.caption(t["draft_note"])
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
        st.caption(t["run_info"].format(model=res["model"], level=res["thinking_level"], runs=res["runs"], date=res["date"]))

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
        rows = []
        for x in tickets:
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
