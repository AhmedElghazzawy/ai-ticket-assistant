"""Web UI for the ticket assistant. Run with: streamlit run src/app.py"""

import time
from collections import Counter
from datetime import datetime
from typing import get_args

import pandas as pd
import streamlit as st
from google.genai import errors

from classifier import classify_ticket
from evaluate import EvalRun, Result, load_run, missed_escalations, save_run, score
from llm import MODEL
from tickets import Priority, load_tickets

st.set_page_config(page_title="Ticket Assistant", page_icon="🎫", layout="wide")

# Priorities in order from least to most urgent, taken from tickets.py
PRIORITIES = list(get_args(Priority))


@st.cache_data
def get_tickets():
    """Load the dataset once and reuse it, instead of re-reading the file on every click."""
    return load_tickets()


def show_api_error(error: errors.APIError) -> None:
    """Turn a Gemini error into a friendly message instead of a crash."""
    if error.code == 429:
        st.error("Gemini's free-tier limit was reached. Wait a minute and try again.")
    else:
        st.error(f"Gemini returned an error ({error.code}). Try again in a moment.")
    with st.expander("Technical details"):
        st.code(str(error))


tickets = get_tickets()

st.title("🎫 University Helpdesk Ticket Assistant")
st.caption(f"Classifies student tickets by category, priority and escalation · model: `{MODEL}`")

try_tab, data_tab, eval_tab = st.tabs(["Try a ticket", "Dataset", "Evaluate"])


# ---------- Tab 1: classify a single ticket ----------
with try_tab:
    samples = {"(write your own)": ""} | {f"{t.id}: {t.text[:70]}": t.text for t in tickets}
    choice = st.selectbox("Start from a sample ticket, or write your own", list(samples))
    text = st.text_area("Ticket text", value=samples[choice], height=120,
                        placeholder="e.g. I can't log in to the student portal...")

    if st.button("Classify", type="primary", disabled=not text.strip()):
        try:
            with st.spinner("Asking Gemini..."):
                result = classify_ticket(text)
        except errors.APIError as error:
            show_api_error(error)
        else:
            if result.escalate:
                st.error("**Escalate to a human.** This ticket should not be handled by the AI alone.")
            else:
                st.success("**The AI can handle this ticket.** No escalation needed.")

            col1, col2, col3 = st.columns(3)
            col1.metric("Category", result.category.replace("_", " ").title(), border=True)
            col2.metric("Priority", result.priority.title(), border=True)
            col3.metric("Escalate", "Yes" if result.escalate else "No", border=True)
            st.markdown(f"**Why:** {result.reason}")

            # If this is one of our labeled tickets, compare with the correct answer
            labeled = next((t for t in tickets if t.text == text), None)
            if labeled:
                st.divider()
                st.markdown(f"**Correct labels for {labeled.id}:** "
                            f"{labeled.category} · {labeled.priority} · escalate={labeled.escalate}")
                if (result.category, result.priority, result.escalate) == \
                        (labeled.category, labeled.priority, labeled.escalate):
                    st.markdown(":green[✓ The model matched every label]")
                else:
                    st.markdown(":orange[✗ The model disagreed with at least one label]")


# ---------- Tab 2: browse the labeled dataset ----------
with data_tab:
    df = pd.DataFrame([t.model_dump() for t in tickets])

    filter1, filter2, filter3 = st.columns(3)
    categories = filter1.multiselect("Category", sorted(df["category"].unique()))
    priorities = filter2.multiselect("Priority", PRIORITIES)
    escalate_filter = filter3.segmented_control("Escalate", ["All", "Yes", "No"], default="All")

    shown = df
    if categories:
        shown = shown[shown["category"].isin(categories)]
    if priorities:
        shown = shown[shown["priority"].isin(priorities)]
    if escalate_filter == "Yes":
        shown = shown[shown["escalate"]]
    elif escalate_filter == "No":
        shown = shown[~shown["escalate"]]

    st.caption(f"Showing {len(shown)} of {len(df)} tickets")
    st.dataframe(
        shown, hide_index=True, width="stretch",
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "text": st.column_config.TextColumn("Ticket", width="large"),
            "escalate": st.column_config.CheckboxColumn("Escalate"),
        },
    )

    chart1, chart2 = st.columns(2)
    with chart1:
        st.subheader("Tickets per category")
        st.bar_chart(df["category"].value_counts(), horizontal=True)
    with chart2:
        st.subheader("Tickets per priority")
        st.bar_chart(df["priority"].value_counts().reindex(PRIORITIES, fill_value=0))


# ---------- Tab 3: run and score the classifier on every ticket ----------
with eval_tab:
    st.markdown("Runs the classifier on all labeled tickets and compares each answer with the correct label. "
                "Results are saved to `eval/results.json`, so you only spend API quota when you click Run.")

    if st.button(f"Run evaluation on {len(tickets)} tickets (about 2 minutes)", type="primary"):
        results = []
        progress = st.progress(0.0, text="Starting...")
        try:
            for i, ticket in enumerate(tickets):
                progress.progress(i / len(tickets), text=f"Classifying {ticket.id} ({i + 1}/{len(tickets)})")
                results.append(Result(ticket=ticket, prediction=classify_ticket(ticket.text)))
                if i < len(tickets) - 1:
                    time.sleep(4)  # free tier allows 15 requests per minute
        except errors.APIError as error:
            progress.empty()
            show_api_error(error)
        else:
            save_run(EvalRun(model=MODEL, finished_at=datetime.now(), results=results))
            progress.empty()
            st.toast("Evaluation finished and saved")

    run = load_run()
    if run is None:
        st.info("No evaluation yet. Click the button above to run the first one.")
    else:
        st.caption(f"Last run: {run.finished_at:%Y-%m-%d %H:%M} · model `{run.model}` · {len(run.results)} tickets")

        scores = score(run.results)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("All labels correct", f"{scores['all']:.0f}%", border=True)
        col2.metric("Category", f"{scores['category']:.0f}%", border=True)
        col3.metric("Priority", f"{scores['priority']:.0f}%", border=True)
        col4.metric("Escalate", f"{scores['escalate']:.0f}%", border=True)

        missed = missed_escalations(run.results)
        if missed:
            st.error(f"**{len(missed)} ticket(s) needed a human but were NOT escalated:** "
                     + ", ".join(r.ticket.id for r in missed))
        else:
            st.success("**Safety check passed:** every ticket that needed a human was escalated.")

        st.subheader("Where the model went wrong per label")
        wrong = Counter()
        for r in run.results:
            wrong["category"] += not r.category_ok
            wrong["priority"] += not r.priority_ok
            wrong["escalate"] += not r.escalate_ok
        st.bar_chart(pd.Series(wrong, name="mistakes"), horizontal=True)

        st.subheader("Results per ticket")
        only_wrong = st.toggle("Show only tickets with a mistake", value=True)
        rows = [
            {
                "ok": "✅" if r.all_ok else "❌",
                "id": r.ticket.id,
                "ticket": r.ticket.text,
                "category": r.prediction.category if r.category_ok
                            else f"{r.prediction.category} (expected {r.ticket.category})",
                "priority": r.prediction.priority if r.priority_ok
                            else f"{r.prediction.priority} (expected {r.ticket.priority})",
                "escalate": str(r.prediction.escalate) if r.escalate_ok
                            else f"{r.prediction.escalate} (expected {r.ticket.escalate})",
                "reason": r.prediction.reason,
            }
            for r in run.results
            if not (only_wrong and r.all_ok)
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={"ticket": st.column_config.TextColumn(width="large"),
                                    "reason": st.column_config.TextColumn(width="large")})
