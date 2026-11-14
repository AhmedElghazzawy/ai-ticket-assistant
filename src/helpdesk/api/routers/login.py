"""Staff login: email and password, the one-click demo, logout. Sessions live in a cookie."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from helpdesk.api.deps import COOKIE_NAME, CurrentStaff, ServicesDep
from helpdesk.api.security import client_ip, same_origin
from helpdesk.core.logs import get_logger
from helpdesk.domain.staff import Staff
from helpdesk.services import auth, staff_desk

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(same_origin)])


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class LoginOptions(BaseModel):
    demo: bool


def set_session_cookie(response: Response, token: str, secure: bool) -> None:
    """Put a new session token in the cookie (used by the normal and the demo login)."""
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=auth.SESSION_HOURS * 3600,
        httponly=True,  # page scripts cannot read it, so an XSS bug cannot steal the session
        secure=secure,  # COOKIE_SECURE: only over https (false only for plain-http development)
        samesite="lax",  # not sent with requests that other websites start
        path="/api",  # only the API needs it
    )


@router.get("/options")
def login_options(services: ServicesDep) -> LoginOptions:
    """What the login page can offer (the demo button only where DEMO_MODE is on)."""
    return LoginOptions(demo=services.settings.demo_mode)


@router.post("/demo")
def demo_log_in(response: Response, services: ServicesDep) -> Staff:
    """One click: log in as the demo staff member with a fresh queue of sample tickets."""
    if not services.settings.demo_mode:
        raise HTTPException(status_code=404, detail="Not found.")
    with services.pool.connection() as db:
        staff_member = staff_desk.start_demo(db)
        token = auth.create_session(db, staff_member.id)
        set_session_cookie(response, token, services.settings.cookie_secure)
    logger.info("demo_login")
    return staff_member


@router.post("/login")
def log_in(body: LoginIn, request: Request, response: Response, services: ServicesDep) -> Staff:
    """Check email and password, start a session, set the cookie. One message for every failure,
    so nobody learns whether an email exists."""
    ip = client_ip(request, services.settings.client_ip_header)
    with services.pool.connection() as db:
        try:
            staff_member = auth.authenticate(db, body.email, body.password, ip)
        except auth.TooManyAttempts:
            logger.warning("login_blocked")  # no email in logs: it is personal data
            raise HTTPException(
                status_code=429, detail="Too many attempts. Try again later."
            ) from None
        if staff_member is None:
            logger.info("login_failed")
            raise HTTPException(status_code=401, detail="Wrong email or password.")
        token = auth.create_session(db, staff_member.id)
        set_session_cookie(response, token, services.settings.cookie_secure)
    logger.info("login", staff_id=staff_member.id)
    return staff_member


@router.post("/logout")
def log_out(request: Request, response: Response, services: ServicesDep) -> dict[str, str]:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with services.pool.connection() as db:
            auth.end_session(db, token)
    response.delete_cookie(COOKIE_NAME, path="/api")
    return {"status": "logged out"}


@router.get("/me")
def me(staff_member: CurrentStaff) -> Staff:
    return staff_member
