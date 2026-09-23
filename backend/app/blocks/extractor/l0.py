"""Offline RU/RO signal rules. Report text is never executed as instructions."""

import re

from app.blocks.geo import haversine_m
from app.contracts.models import Extracted, Report, Verification

_SIGNALS = {
    "открытый люк": r"открыт\w* люк|нет крышки|capac\w* lips|fără capac",
    "опасность для людей": r"опасн|дети|реб[её]нок|pericol|copii|copil",
    "пострадавший": r"травм|пострада|упал|rănit|rănire|căzut",
}
_OBJECTS = {
    "manhole": r"люк|capac|cămin",
    "pothole": r"ям[аыуе]|groap|grop|провал асфальта",
    "streetlight": r"фонар|освещ|ilumin|felinar",
    "garbage": r"мусор|gunoi|deșeu",
    "tree": r"дерев|ветк|copac|creang",
    "water_leak": r"теч[её]т вода|утечк|scurgere|conduct",
}


def extract(report: Report) -> Extracted:
    text = report.text.casefold()
    signals = [label for label, pattern in _SIGNALS.items() if re.search(pattern, text)]
    category = next(
        (key for key, pattern in _OBJECTS.items() if re.search(pattern, text)), None
    )
    return Extracted(
        hazard_signals=signals,
        object=category,
        suggested_category=category,
        injured="пострадавший" in signals,
    )


def verify(report: Report, nearby: list[Report]) -> Verification:
    if report.confirmations >= 2:
        return Verification(
            status="confirmed",
            confidence=1,
            reasons=["Два или более подтверждений жителей"],
        )
    reasons = []
    if not report.photo_url:
        reasons.append("Нет фотографии")
    if report.confirmations == 0:
        reasons.append("Нет подтверждений жителей")
    if not any(
        r.id != report.id
        and r.status == "open"
        and r.category == report.category
        and haversine_m(r.location, report.location) <= 100
        for r in nearby
    ):
        reasons.append("Рядом нет других обращений о такой проблеме")
    if not report.address and not re.search(
        r"\d|возле|у входа|останов|lângă|strad", report.text.casefold()
    ):
        reasons.append("Нет адреса или конкретного ориентира")
    if re.search(
        r"настоящим|комплексн|инфраструктурн|в целях|уважаем\w* орган|în vederea",
        report.text.casefold(),
    ):
        reasons.append("Шаблонные формулировки")
    suspicious = len(reasons) >= 3
    return Verification(
        status="suspicious" if suspicious else "plausible",
        reasons=reasons,
        confidence=0.3 if suspicious else 0.8,
    )
