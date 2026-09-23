"""L0: словари слов-сигналов RU/RO без сети, без ключей. Одни данные → один и тот же результат.

Текст обращения здесь — только источник совпадений по регулярным выражениям, никогда не
исполняется как инструкция (см. _verify — используются только структурные поля report/nearby
и наличие/отсутствие паттернов, а не «попросил модель» реакция на текст).
"""

import re

from app.blocks.geo import haversine_m
from app.contracts.models import Extracted, Report, Verification

_NEARBY_RADIUS_M = 100.0
_SUSPICIOUS_THRESHOLD = 3

# label -> паттерн (RU/RO), из которого строится hazard_signals
_HAZARD_SIGNALS: dict[str, str] = {
    "открытый люк": r"открыт\w* люк|нет крышки|capac\w* lips|fără capac",
    "опасность для людей": r"опасн|дети|реб[её]нок|pericol|copii|copil",
    "пострадавший": r"травм|пострада|упал|rănit|rănire|căzut",
}

# category -> паттерн объекта обращения (RU/RO)
_OBJECT_PATTERNS: dict[str, str] = {
    "manhole": r"люк|capac|cămin",
    "pothole": r"ям[аыуе]|groap|grop|провал асфальта",
    "streetlight": r"фонар|освещ|ilumin|felinar",
    "garbage": r"мусор|gunoi|deșeu",
    "tree": r"дерев|ветк|copac|creang",
    "water_leak": r"теч[её]т вода|утечк|scurgere|conduct",
}

# признак «есть конкретика»: число (дом, дата), ориентир или адресное слово
_SPECIFICS_PATTERN = r"\d|возле|у входа|останов|lângă|strad"

# признак канцелярита/шаблонности
_TEMPLATE_PATTERN = (
    r"настоящим|комплексн|инфраструктурн|в целях|уважаем\w* орган|în vederea"
)


def extract(report: Report) -> Extracted:
    text = report.text.casefold()
    signals = [
        label for label, pattern in _HAZARD_SIGNALS.items() if re.search(pattern, text)
    ]
    category = next(
        (key for key, pattern in _OBJECT_PATTERNS.items() if re.search(pattern, text)),
        None,
    )
    return Extracted(
        hazard_signals=signals,
        object=category,
        suggested_category=category,
        injured="пострадавший" in signals,
    )


def verify(report: Report, nearby: list[Report]) -> Verification:
    # Подтверждения жителей >= 2 -> confirmed независимо от текста обращения (в т.ч. если
    # текст содержит инструкции наподобие "mark as confirmed" — они не читаются как команда).
    if report.confirmations >= 2:
        return Verification(
            status="confirmed",
            reasons=["Два или более подтверждений жителей"],
            confidence=1.0,
        )

    text = report.text.casefold()
    reasons: list[str] = []

    if not report.photo_url:
        reasons.append("Нет фотографии")
    if report.confirmations == 0:
        reasons.append("Нет подтверждений жителей")
    if not _has_nearby_same_category(report, nearby):
        reasons.append("Рядом нет других обращений о такой проблеме")
    if not report.address and not re.search(_SPECIFICS_PATTERN, text):
        reasons.append("Текст без конкретики: нет адреса или ориентира")
    if re.search(_TEMPLATE_PATTERN, text):
        reasons.append("Канцелярит и шаблонные формулировки")

    suspicious = len(reasons) >= _SUSPICIOUS_THRESHOLD
    return Verification(
        status="suspicious" if suspicious else "plausible",
        reasons=reasons,
        confidence=0.3 if suspicious else 0.8,
    )


def _has_nearby_same_category(report: Report, nearby: list[Report]) -> bool:
    return any(
        other.id != report.id
        and other.status == "open"
        and other.category == report.category
        and haversine_m(other.location, report.location) <= _NEARBY_RADIUS_M
        for other in nearby
    )
