"""Web page for the ticket assistant. Run with: .venv/bin/streamlit run src/app.py"""

import streamlit as st

from llm import ask
from tickets import TICKETS_PATH, load_tickets

# Every text on the page, in both languages. Add new texts to both.
TEXTS = {
    "tr": {
        "title": "Üniversite Yardım Masası Asistanı",
        "tab_try": "Ticket dene",
        "tab_data": "Veri seti",
        "ticket_box": "Öğrencinin ticket'ı",
        "send": "Gönder",
        "empty": "Lütfen bir ticket yazın.",
        "thinking": "Model düşünüyor...",
        "reply": "Taslak cevap",
        "reply_language": "Turkish",
        "no_data": "Henüz ticket yok. data/tickets/tickets.jsonl dosyasını oluşturun.",
        "count": "Ticket sayısı",
        "filter": "Dile göre filtrele",
        "all": "Hepsi",
    },
    "en": {
        "title": "University Helpdesk Assistant",
        "tab_try": "Try a ticket",
        "tab_data": "Dataset",
        "ticket_box": "The student's ticket",
        "send": "Send",
        "empty": "Please write a ticket.",
        "thinking": "The model is thinking...",
        "reply": "Draft reply",
        "reply_language": "English",
        "no_data": "No tickets yet. Create data/tickets/tickets.jsonl.",
        "count": "Number of tickets",
        "filter": "Filter by language",
        "all": "All",
    },
}

st.set_page_config(page_title="Helpdesk Assistant", page_icon="🎓")

language = st.sidebar.radio("Dil / Language", ["tr", "en"], format_func=str.upper)
t = TEXTS[language]  # t["title"] gives the title in the chosen language

st.title(t["title"])
tab_try, tab_data = st.tabs([t["tab_try"], t["tab_data"]])

with tab_try:
    ticket = st.text_area(t["ticket_box"], height=120)
    if st.button(t["send"], type="primary"):
        if not ticket.strip():
            st.warning(t["empty"])
        else:
            prompt = (
                "You are a university helpdesk assistant. "
                f"Reply briefly in {t['reply_language']} to this ticket:\n\n{ticket}"
            )
            try:
                with st.spinner(t["thinking"]):
                    reply = ask(prompt)
                st.subheader(t["reply"])
                st.write(reply)
            except Exception as error:  # noqa: BLE001 - on purpose: show any problem on the page, not a crash
                st.error(f"{type(error).__name__}: {error}")

with tab_data:
    if not TICKETS_PATH.exists():
        st.info(t["no_data"])
    else:
        try:
            tickets = load_tickets()
        except ValueError as error:  # a bad line: show which one, like the terminal does
            st.error(str(error))
        else:
            choice = st.radio(t["filter"], [t["all"], "tr", "en"], horizontal=True)
            rows = [x.model_dump() for x in tickets if choice == t["all"] or x.language == choice]
            st.metric(t["count"], len(rows))
            st.dataframe(rows, hide_index=True)  # full width is the default
