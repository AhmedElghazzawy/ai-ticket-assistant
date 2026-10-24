"""A test app with helpers: send a ticket, choose the fake pipeline, log in as staff.

Each test gets its own app from the `api` / `make_api` fixtures (conftest.py): its own database
schema, its own rate-limit counters, and a pipeline that must be chosen (no Gemini calls).
"""

from contextlib import AbstractContextManager
from typing import NoReturn

import httpx2
from fastapi import FastAPI
from fastapi.testclient import TestClient

from helpdesk import auth
from helpdesk.api.deps import Pipeline, Services
from helpdesk.auth import Role
from helpdesk.domain.offices import OfficeId
from helpdesk.storage.db import Connection

PASSWORD = "correct horse battery"


def no_pipeline(*args: object) -> NoReturn:
    """The default: a test that reaches the pipeline without choosing a fake one fails loudly,
    instead of calling the paid model."""
    raise AssertionError("This test sent a ticket without choosing a fake pipeline.")


class Api:
    """One app under test and a browser (TestClient) talking to it."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.client = TestClient(app)

    @property
    def services(self) -> Services:
        services: Services = self.app.state.services
        return services

    def use_pipeline(self, pipeline: Pipeline) -> None:
        self.services.pipeline = pipeline

    def database(self) -> AbstractContextManager[Connection]:
        return self.services.pool.connection()

    def ask(
        self,
        text: str = "Harç iade edilir mi?",
        language: str = "tr",
        client: TestClient | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx2.Response:
        """A student sends a ticket (from `client`, default the main browser)."""
        sender = client or self.client
        return sender.post(
            "/api/tickets", json={"text": text, "language": language}, headers=headers
        )

    def visitor(self, ip: str) -> TestClient:
        """Another visitor, with their own address."""
        return TestClient(self.app, client=(ip, 50000))

    def browser(self) -> TestClient:
        """A fresh browser over https, so the Secure session cookie is sent back."""
        return TestClient(self.app, base_url="https://testserver")

    def staff(self, role: Role = "admin", office: OfficeId | None = None) -> TestClient:
        """A browser logged in as a new staff member."""
        email = f"{role}-{office}@bilecik.edu.tr"
        with self.database() as db:
            auth.create_staff(db, email, "Test", role, office, PASSWORD)
        browser = self.browser()
        login = browser.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert login.is_success
        return browser
