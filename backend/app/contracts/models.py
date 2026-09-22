"""Канонические модели CityTriage. ЕДИНСТВЕННЫЙ язык общения между блоками.

Менять этот файл могут только владельцы контрактов (Арсений, Некит) отдельным PR
`contracts/<что-меняем>`. Блоки импортируют модели отсюда и НЕ заводят свои копии.
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Extracted(BaseModel):
    """Что LLM/правила вытащили из текста обращения (блок L1)."""

    hazard_signals: list[str] = []  # ["открытый люк", "ребёнок упал"]
    object: str | None = None  # "яма", "фонарь"
    injured: bool = False
    suggested_category: str | None = None


class Verification(BaseModel):
    """Проверка на «нейрослоп» и неправдоподобные обращения (блок L1)."""

    status: Literal["unverified", "plausible", "suspicious", "confirmed"] = "unverified"
    reasons: list[str] = []
    confidence: float = Field(default=0.0, ge=0, le=1)


class Report(BaseModel):
    """Одно обращение. Поля совместимы с Open311 GeoReport v2 service_request."""

    id: str
    source: Literal["dataset", "citizen", "voice"] = "dataset"
    category: str  # одно из CATEGORIES
    text: str
    lang: Literal["ro", "ru", "en"] | None = None
    location: GeoPoint
    address: str | None = None
    photo_url: str | None = None
    created_at: datetime
    status: Literal["open", "in_progress", "resolved", "rejected"] = "open"
    cluster_id: str | None = None
    confirmations: int = 0  # «у меня тоже» / «всё ещё там» от жителей
    extracted: Extracted | None = None
    verification: Verification | None = None


class DupLink(BaseModel):
    """Почему два обращения считаются одной проблемой."""

    a: str  # report id
    b: str  # report id
    distance_m: float
    text_sim: float = Field(ge=0, le=1)


class Cluster(BaseModel):
    """Одна реальная проблема = одно или несколько обращений."""

    id: str
    category: str
    centroid: GeoPoint
    report_ids: list[str]
    links: list[DupLink] = []
    first_reported_at: datetime
    last_reported_at: datetime
    status: Literal["open", "planned", "in_progress", "resolved"] = "open"


class Factor(BaseModel):
    """Вклад одного фактора в приоритет. Из этого фронт рисует PriorityBar."""

    code: str  # HZ DM AG SP RC EX WX VF
    label: str  # человекочитаемо, на русском
    score: float | None  # 0..1; None = данных нет, фактор исключён из суммы
    weight: float
    points: float  # вклад в итоговые 0..100
    evidence: list[str] = []


class Priority(BaseModel):
    cluster_id: str
    score: float = Field(ge=0, le=100)
    factors: list[Factor]
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = False


class Weather(BaseModel):
    at: datetime
    precipitation_mm: float
    wind_ms: float
    temp_c: float
    source: str  # "open-meteo" | "fixture"


class Event(BaseModel):
    """Городское мероприятие: забег, концерт, ярмарка. Используется только дополнительным блоком X1."""

    id: str
    title: str
    location: GeoPoint
    radius_m: int = 300
    starts_at: datetime
    ends_at: datetime
    expected_people: int = 0
    source: str = "manual"  # "manual" | "fixture" | домен из allowlist


class InfraObject(BaseModel):
    id: str
    kind: Literal["school", "kindergarten", "hospital", "stop"]
    name: str
    location: GeoPoint


class Context(BaseModel):
    """Всё внешнее, что влияет на решения. Собирает блок B5."""

    now: datetime
    weather: Weather | None = None
    events: list[Event] = []
    infrastructure: list[InfraObject] = []


class Crew(BaseModel):
    id: str
    name: str
    skills: list[str]  # одно из SKILLS
    start: GeoPoint
    shift_start: datetime
    shift_end: datetime


class Job(BaseModel):
    """Одна остановка бригады. Может закрывать несколько кластеров рядом."""

    id: str
    cluster_ids: list[str]
    location: GeoPoint
    skill: str
    service_min: int
    priority: int = Field(ge=0, le=100)
    deadline: datetime | None = None  # напр. «до начала мероприятия»


class Decision(BaseModel):
    """Журнал решений: что и почему изменило план. Показывается оператору."""

    kind: Literal[
        "defer", "boost", "batch", "deadline", "unassigned", "param", "replan", "review"
    ]
    subject_id: str  # job/cluster id или имя параметра
    reason: str
    by: Literal["rule", "llm", "operator"]


class RouteStop(BaseModel):
    job_id: str
    location: GeoPoint
    arrival: datetime
    departure: datetime
    status: Literal["pending", "arrived", "done", "failed"] = "pending"


class CrewRoute(BaseModel):
    crew_id: str
    stops: list[RouteStop]
    geometry: list[GeoPoint] = []  # линия для карты
    drive_min: int = 0
    work_min: int = 0


class Plan(BaseModel):
    id: str
    day: date
    routes: list[CrewRoute]
    unassigned: list[str] = []  # job ids
    total_priority: int = 0
    baseline_total_priority: int = 0  # порядок «по времени поступления»
    decisions: list[Decision] = []
    engine: str = "greedy"  # "greedy" | "vroom"
    status: Literal["draft", "approved", "superseded"] = (
        "draft"  # бригады видят только approved
    )
    version: int = 1  # растёт при каждой перестройке
    approved_by: str | None = None  # email руководителя; ИИ утверждать план не может


class JobUpdate(BaseModel):
    """Сообщение бригады с выезда. «failed» запускает перестройку плана."""

    job_id: str
    crew_id: str
    status: Literal["arrived", "done", "failed"]
    at: datetime
    photo_url: str | None = None  # обязательно для done
    reason: (
        Literal["no_access", "needs_other_skill", "not_found", "weather", "other"]
        | None
    ) = None  # для failed
    needs_skill: str | None = None  # для needs_other_skill: одно из SKILLS
    note: str | None = None


class OperatorRun(BaseModel):
    """Один самостоятельный проход ИИ-оператора. Лента этих записей — «что сделал оператор»."""

    id: str
    trigger: Literal["import", "new_report", "job_update", "weather", "manual"]
    at: datetime
    reports_seen: int
    clusters_total: int
    clusters_new: int
    needs_review: list[str] = []  # cluster ids, которые ждут человека
    plan_id: str | None = None  # черновик плана, который оператор собрал или перестроил
    decisions: list[Decision] = []
    summary: str = ""  # человеческим языком; пишет L2, при LLM=off — шаблон


# --- TripRequest / HazardOnRoute / Trip — только для дополнительных блоков B7 и F7 ---
class TripRequest(BaseModel):
    origin: GeoPoint
    destination: GeoPoint
    depart_at: datetime | None = None


class HazardOnRoute(BaseModel):
    cluster_id: str
    category: str
    priority: float
    location: GeoPoint
    distance_from_start_m: float


class Trip(BaseModel):
    """Маршрут жителя A→B с проблемами и мероприятиями по пути."""

    geometry: list[GeoPoint]
    duration_min: float
    distance_m: float
    hazards: list[HazardOnRoute] = []
    events: list[Event] = []
    engine: str = "straight"  # "straight" | "ors"


class UIState(BaseModel):
    """Что сейчас на экране. Так ассистент «видит карту» — без пикселей."""

    role: Literal["supervisor", "crew", "citizen"] = "supervisor"
    bbox: tuple[float, float, float, float] | None = (
        None  # min_lon, min_lat, max_lon, max_lat
    )
    selected_cluster_id: str | None = None
    filters: dict[str, Any] = {}


class UIAction(BaseModel):
    kind: Literal[
        "focus_cluster",
        "show_plan",
        "show_run",
        "show_crew",
        "set_filter",
        "show_trip",
        "open_report_form",
    ]
    payload: dict[str, Any] = {}


class PendingAction(BaseModel):
    """Действие, которое ИИ-оператор сам выполнить не вправе: ждёт решения руководителя."""

    id: str
    tool: str  # имя write-инструмента
    args: dict[str, Any]
    summary: str  # что именно будет сделано, человеческим языком


class AssistantRequest(BaseModel):
    session_id: str
    message: str
    ui_state: UIState = UIState()


class AssistantResponse(BaseModel):
    text: str
    actions: list[UIAction] = []
    pending: PendingAction | None = None
    trace: list[
        str
    ] = []  # пройденные узлы графа: ["intent:build_plan", "tool:solve", ...]


CATEGORIES = [
    "pothole",  # яма
    "streetlight",  # освещение
    "garbage",  # мусор
    "manhole",  # люк
    "tree",  # упавшее дерево / ветки
    "water_leak",  # утечка воды
    "traffic_sign",  # знак / светофор
    "public_space",  # скамейки, площадки, прочее
]

SKILLS = ["road", "electric", "sanitation", "water", "green"]

CATEGORY_TO_SKILL = {
    "pothole": "road",
    "manhole": "road",
    "traffic_sign": "road",
    "streetlight": "electric",
    "garbage": "sanitation",
    "public_space": "sanitation",
    "water_leak": "water",
    "tree": "green",
}

CATEGORY_SERVICE_MIN = {
    "pothole": 45,
    "manhole": 30,
    "traffic_sign": 30,
    "streetlight": 25,
    "garbage": 20,
    "public_space": 40,
    "water_leak": 90,
    "tree": 60,
}
