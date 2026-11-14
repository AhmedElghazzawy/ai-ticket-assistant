"""A staff member of a BŞEÜ office, as the login and the staff console see them."""

from typing import Literal

from pydantic import BaseModel

from helpdesk.domain.offices import OfficeId

Role = Literal["staff", "admin"]


class Staff(BaseModel):
    id: int
    email: str
    name: str
    role: Role
    office: OfficeId | None  # None for admins: they see every office
    demo: bool = False  # the demo account sees only demo tickets
