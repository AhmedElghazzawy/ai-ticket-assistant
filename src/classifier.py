"""Classify a support ticket into category, priority and escalate using Gemini."""

import time

from google.genai import types
from pydantic import BaseModel

from llm import MODEL, client
from tickets import Category, Priority, load_tickets


class Classification(BaseModel):
    # reason comes first so the model explains its thinking before it decides
    reason: str
    category: Category
    priority: Priority
    escalate: bool


INSTRUCTIONS = """\
You are the triage system for a university student helpdesk.
Read the student's ticket and classify it.

Categories:
- account_access: logins, passwords, locked accounts, two-factor authentication
- registration: adding or dropping classes, prerequisites, waitlists, registration dates
- billing: tuition, fees, charges, refunds, payment plans, financial aid payments
- it_support: Wi-Fi, software, printers, online platforms, devices
- academic_records: grades, transcripts, enrollment letters, name changes on records
- housing: dorms, room problems, roommates, housing applications
- other: anything that fits none of the above

Priority:
- urgent: someone's safety or wellbeing is at risk right now
- high: blocks something time-sensitive, or money, grades or account security are at stake
- medium: a real problem, but not time-critical
- low: a general question or request for information

Escalate to a human (escalate = true) when ANY of these apply:
- a safety threat, harassment, or signs of self-harm or crisis
- an account may be compromised (phishing, someone else has the password)
- the student needs a policy exception (missed deadline due to an emergency)
- a money dispute that needs a refund or correction
- a grade or exam result dispute
- legal threats, or repeated contacts with no answer
Being frustrated or upset is NOT on its own a reason to escalate.

In reason, explain your decision in one short sentence."""


def classify_ticket(text: str) -> Classification:
    """Send one ticket to Gemini and get back a validated Classification."""
    response = client.models.generate_content(
        model=MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCTIONS,
            response_mime_type="application/json",
            response_schema=Classification,
            temperature=0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    return response.parsed


if __name__ == "__main__":
    for ticket in load_tickets():
        result = classify_ticket(ticket.text)
        expected = (ticket.category, ticket.priority, ticket.escalate)
        predicted = (result.category, result.priority, result.escalate)
        mark = "OK  " if predicted == expected else "DIFF"
        print(f"{mark} {ticket.id}: {ticket.text[:60]}")
        if predicted != expected:
            print(f"       expected:  {expected}")
            print(f"       predicted: {predicted}")
            print(f"       reason:    {result.reason}")
        time.sleep(4)  # free tier allows 15 requests per minute, so wait between tickets
