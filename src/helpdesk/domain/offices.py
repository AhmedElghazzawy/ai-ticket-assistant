"""The real BŞEÜ offices and which category each one handles."""

from typing import Literal

from helpdesk.domain.tickets import Category

# The real BŞEÜ offices (docs/PROJECT_BRIEF.md). IDs travel through the system; the page shows the name
# in the reader's language.
OfficeId = Literal["it", "student_affairs", "fees", "sks", "duty"]

OFFICE_OF: dict[Category, OfficeId] = {
    "account_access": "it",
    "it_support": "it",
    "registration": "student_affairs",
    "academic_records": "student_affairs",
    "billing": "fees",
    "campus_life": "sks",
    "other": "duty",
}

OFFICE_NAMES: dict[str, dict[OfficeId, str]] = {
    "tr": {
        "it": "Bilgi İşlem Daire Başkanlığı",
        "student_affairs": "Öğrenci İşleri Daire Başkanlığı",
        "fees": "Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü",
        "sks": "Sağlık, Kültür ve Spor (SKS) Daire Başkanlığı",
        "duty": "Öğrenci İşleri nöbetçi personeli",
    },
    "en": {
        "it": "IT Department (Bilgi İşlem)",
        "student_affairs": "Student Affairs (Öğrenci İşleri)",
        "fees": "Student Affairs, Fees Office (Harçlar Şube Müdürlüğü)",
        "sks": "Health, Culture and Sports Office (SKS)",
        "duty": "Student Affairs duty staff",
    },
}
