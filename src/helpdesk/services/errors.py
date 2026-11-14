"""Why a use case refused, without HTTP: the API turns each one into a status code (api/app.py), so
the same rule gives the same answer from the API, a script or a test. The message is safe to show."""


class NotFound(Exception):
    """No such ticket, or the caller may not see it (both look the same on purpose)."""


class Conflict(Exception):
    """The ticket is not in a state that allows this (e.g. staff already answered it)."""


class AssistantUnavailable(Exception):
    """The AI pipeline failed; the student gets a short message, the logs get the error type."""
