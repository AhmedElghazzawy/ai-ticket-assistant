"""Web page for the ticket assistant. Run with: .venv/bin/streamlit run src/app.py"""

import streamlit as st

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
        "ticket_box": "Öğrencinin ticket'ı",
        "example": "Veri setinden örnek seç",
        "example_hint": "Bir örnek seçin veya kendiniz yazın",
        "send": "Gönder",
        "empty": "Lütfen bir ticket yazın.",
        "thinking": "Model düşünüyor...",
        "reply": "Taslak cevap",
        "reply_language": "Turkish",
        "reply_hint": "Bir ticket yazıp Gönder'e basın.",
        "not_yet": "Kategori, öncelik ve escalation etiketleri bir sonraki adımda (Step 4) burada görünecek.",
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
        "ticket_box": "The student's ticket",
        "example": "Pick an example from the dataset",
        "example_hint": "Pick an example or write your own",
        "send": "Send",
        "empty": "Please write a ticket.",
        "thinking": "The model is thinking...",
        "reply": "Draft reply",
        "reply_language": "English",
        "reply_hint": "Write a ticket and press Send.",
        "not_yet": "Category, priority and escalation labels will appear here in the next step (Step 4).",
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
DONE_STEPS = 3  # how many of the steps above are finished; raise it as the project grows

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
tab_try, tab_data = st.tabs([t["tab_try"], t["tab_data"]])

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
        st.subheader(t["reply"])
        if send and not ticket.strip():
            st.warning(t["empty"])
        elif send:
            prompt = (
                "You are a university helpdesk assistant. "
                f"Reply briefly in {t['reply_language']} to this ticket:\n\n{ticket}"
            )
            try:
                with st.spinner(t["thinking"]):
                    reply = ask(prompt)
                with st.container(border=True):
                    st.markdown(reply)
            except Exception as error:  # noqa: BLE001 - on purpose: show any problem on the page, not a crash
                st.error(f"{type(error).__name__}: {error}")
        else:
            st.caption(t["reply_hint"])
        st.info(t["not_yet"])

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
