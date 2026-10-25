"""Create a staff account (there is no public sign-up).

  uv run python tools/add_staff.py ayse@bilecik.edu.tr "Ayşe Yılmaz" --office it
  uv run python tools/add_staff.py admin@bilecik.edu.tr "Admin" --admin
In Docker: docker compose exec app python tools/add_staff.py ...

The password is typed in hidden (never on screen, never in the shell history).
"""

import argparse
import sys
from contextlib import closing
from getpass import getpass
from typing import get_args

from helpdesk import auth
from helpdesk.domain.offices import OfficeId
from helpdesk.storage.db import connect


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a staff account.")
    parser.add_argument("email")
    parser.add_argument("name")
    who = parser.add_mutually_exclusive_group(required=True)
    who.add_argument("--office", choices=get_args(OfficeId), help="the office this person works in")
    who.add_argument("--admin", action="store_true", help="sees every office")
    args = parser.parse_args()

    password = getpass("Password (at least 12 characters): ")
    if getpass("Again: ") != password:
        sys.exit("The two passwords differ.")
    with closing(connect()) as db:  # DATABASE_URL: local Docker, or Neon in production
        try:
            role: auth.Role = "admin" if args.admin else "staff"
            auth.create_staff(db, args.email, args.name, role, args.office, password)
        except ValueError as error:
            sys.exit(str(error))
    print(f"Created {args.email} ({'admin' if args.admin else args.office}).")


if __name__ == "__main__":
    main()
