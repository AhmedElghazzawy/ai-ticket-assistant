"""Protection for public endpoints: per-visitor rate limits, the visitor's address, CSRF."""

import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

from fastapi import HTTPException, Request


class RateLimiter:
    """Per-visitor limits, counted in memory only: an IP address is personal data, so it is never
    written to disk or logs. Resets on restart and works for one server: fine for our single
    machine (several servers would need a shared counter, e.g. Redis)."""

    def __init__(self, limits: tuple[tuple[int, float], ...] = ((5, 60.0), (30, 86_400.0))):
        self.limits = limits  # (how many, within how many seconds)
        self.seen: defaultdict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()  # requests run on several threads at once

    def allow(self, visitor: str) -> bool:
        now = time.monotonic()
        longest = max(window for _, window in self.limits)
        with self.lock:
            times = self.seen[visitor]
            while times and now - times[0] > longest:  # forget what is too old to matter
                times.popleft()
            if any(sum(now - t < window for t in times) >= most for most, window in self.limits):
                return False
            times.append(now)
            return True


def client_ip(request: Request, header: str) -> str:
    """The visitor's address, for rate limits only (never stored or logged).

    Behind a hosting proxy every request seems to come from the proxy. `header` (CLIENT_IP_HEADER)
    names the header in which the proxy puts the real visitor (Render: "cf-connecting-ip"). Empty:
    the header is ignored, because a visitor could fake it. NOT X-Forwarded-For with "trust all":
    its left-most address is written by the visitor, so a bot could invent a new address every time.
    """
    if header and (forwarded := request.headers.get(header)):
        return forwarded.strip()
    return request.client.host if request.client else "unknown"


def same_origin(request: Request) -> None:
    """CSRF guard: a change (POST, PATCH, ...) coming from another website is refused. Browsers
    send an Origin header with such requests; tools like curl send none and are not affected."""
    origin = request.headers.get("origin")
    unsafe = request.method not in ("GET", "HEAD")
    if unsafe and origin and urlparse(origin).netloc != request.headers.get("host"):
        raise HTTPException(status_code=403, detail="Request from another website refused.")
