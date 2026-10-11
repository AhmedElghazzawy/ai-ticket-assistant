"""Structured logs: every event is one line with named fields (JSON in production).

Rule: NEVER log what a student wrote (personal data, KVKK). Log its length instead.
"""

import logging
import os
import sys

import structlog


def configure() -> None:
    """Set up logging once. LOG_FORMAT=json gives one JSON object per line (for servers and
    log tools); otherwise readable, coloured lines for a person at a terminal."""
    # Read directly, not through config.Settings: logging must work before (and without) the API key.
    json_lines = os.getenv("LOG_FORMAT", "console").lower() == "json"
    renderer = (
        structlog.processors.JSONRenderer()
        if json_lines
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # adds the request_id bound for this request
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    """A logger whose lines say which file they come from. It stays LAZY: modules create their
    logger while being imported, before configure() runs; a lazy logger reads the configuration
    on first use. (bind() here would lock it to structlog's defaults: a bug we hit.)"""
    logger: structlog.typing.FilteringBoundLogger = structlog.get_logger(module=name)
    return logger
