# B6 · Диспетчер: план и маршруты бригад

> **Контракт блока.** Вставь этот файл целиком в нейронку. Работай строго по нему.

| | |
|---|---|
| Блок | `B6` · `dispatch` · группа BACKEND |
| Владелец | **Женёк** |
| Запасной | Некит |
| Первое ревью | Некит |
| Одобряет merge | Арсений или Некит (не автор PR) |
| Ветка | `feat/B6-<кратко>` → PR в `pair/backend` |
| Зависит от | B2, B3, B4, B5 |
| Кто использует | B0, B8, F3, L3 |

## Цель
Ответ на вопрос задачи «как распределить ресурсы». Из кластеров сделать задачи, соседние объединить в один выезд («закрыть 3–4 ямы за раз») и построить маршруты бригад на день. Главное отличие проекта.

## Разрешённые пути
Можно создавать и менять ТОЛЬКО эти файлы:
- `backend/app/blocks/dispatch/**`
- `backend/app/api/routes/plan.py`
- `backend/tests/blocks/dispatch/**`

## Порт (что блок обязан предоставить)
```python
# backend/app/blocks/dispatch/__init__.py
BATCH_RADIUS_M = 450       # «один участок улицы»

def make_jobs(clusters: list[Cluster], priorities: dict[str, Priority], ctx: Context) -> tuple[list[Job], list[Decision]]: ...
def solve(jobs: list[Job], crews: list[Crew], ctx: Context) -> Plan: ...
def replan(plan: Plan, update: JobUpdate, jobs: list[Job], crews: list[Crew], ctx: Context) -> Plan: ...
def baseline_total_priority(jobs: list[Job], crews: list[Crew]) -> int: ...
```
`make_jobs`:
- навык и длительность — из `CATEGORY_TO_SKILL` / `CATEGORY_SERVICE_MIN` (contracts);
- **объединение:** кластеры одного навыка в пределах `BATCH_RADIUS_M` от первого (по убыванию приоритета) → один `Job`: `cluster_ids=[...]`, `service_min = сумма × 0.8`, `priority = max`, `Decision.kind="batch"`;
- `Job.deadline` в ядре всегда `None`; его выставляет только дополнительный блок X1, но `solve` обязан его учитывать, если он есть;
- кластеры с `needs_review=True` в план НЕ попадают (`Decision.kind="unassigned"`, причина «требует проверки оператором»).

`solve`: учитывает `skills`, смену бригады, `deadline`; максимизирует сумму `priority` выполненных задач; всё, что не влезло, → `unassigned` + `Decision`. `baseline` = та же смена, но задачи в порядке поступления.
`replan` (бригада сообщила `failed` или закончила раньше):
- остановки со статусом `done`/`arrived` не трогаются; бригады стартуют с текущей точки и текущего времени;
- `failed` + `needs_other_skill` → задача получает навык `needs_skill` и уходит подходящей бригаде;
- `failed` + `not_found` → задача снимается, кластер получает `needs_review` (`Decision.kind="review"`, «бригада не нашла проблему»);
- `failed` + `weather`/`no_access`/`other` → задача возвращается в конец очереди этого дня или в `unassigned`;
- результат: НОВЫЙ `Plan` с `version+1`, `status="draft"`, в `decisions` — `kind="replan"` с тем, что изменилось; старый план остаётся действующим, пока новый не утверждён.

Роуты (`/api/v1/plan`): `POST /plan {day}` → черновик; `GET /plan/current` → действующий approved; `GET /plan/draft` → последний черновик; `GET /plan/{id}`;
`POST /plan/{id}/approve` (ТОЛЬКО роль supervisor-человек) → `status="approved"`, прежний → `superseded`; `GET /crews`.

## Модели контрактов, которые использует блок
Импорт: `from app.contracts.models import ...` (фронт — типы из сгенерированного клиента). Не менять, не копировать.
```python
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


class Priority(BaseModel):
    cluster_id: str
    score: float = Field(ge=0, le=100)
    factors: list[Factor]
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = False


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


class Context(BaseModel):
    """Всё внешнее, что влияет на решения. Собирает блок B5."""

    now: datetime
    weather: Weather | None = None
    events: list[Event] = []
    infrastructure: list[InfraObject] = []
```

## Уровни (заменяемость)
| Уровень | Что сделать |
|---|---|
| **L0** | `ROUTER=greedy`: сортировка по `priority / service_min`, ближайшая подходящая бригада, время в пути = haversine / 30 км/ч, `geometry` = прямые линии. |
| **L1** | `ROUTER=vroom`: задача в формате VROOM (`jobs[].priority/skills/service/time_windows`, `vehicles[].skills/time_window/start`) через `openrouteservice` optimization API; `geometry` — из ORS directions. Ошибка/лимит API → откат на greedy, `Plan.engine="greedy"`. |
| **L2** | Локальный `pyvroom` с матрицей из OSRM — без внешнего ключа. |

Переключатель: `ROUTER=greedy|vroom`, `ORS_API_KEY`

## Зависимости, которыми можно пользоваться (уже установлены)
`openrouteservice`, `httpx`

## Критерии приёмки
Ссылки вида `expect.*` — это раздел `expect` в `backend/app/fixtures/demo_city.json`.
1. Fixture (кластер `r006` с `needs_review=True`) → `make_jobs` даёт ровно `expect.jobs_after_batching` = 9 задач; одна из них содержит кластеры всех `expect.site_batch`, её `service_min = 144`.
2. Задача с вручную выставленным `deadline` получает `arrival` раньше дедлайна либо попадает в `unassigned` с причиной.
3. `replan` после `failed/needs_other_skill` по задаче бригады c1: задача ушла бригаде с нужным навыком, выполненные остановки c1 не изменились, `version` вырос, `status="draft"`.
4. `replan` после `failed/not_found`: задачи нет в новом плане, есть `Decision(kind="review")`.
5. `POST /plan/{id}/approve` от роли crew → 403; от supervisor → `approved`, предыдущий план `superseded`.
6. Ни одна бригада не получает задачу не своего навыка; ни один маршрут не выходит за смену.
7. `Plan.total_priority ≥ Plan.baseline_total_priority`.
8. Сценарий `storm`: ямы уходят из плана с `Decision(kind="defer")`, задача `tree` остаётся в плане.
9. Смена всех бригад урезана до 2 часов → `unassigned` не пуст, у каждой невошедшей задачи есть `Decision`.
10. `ROUTER=vroom` без ключа → план всё равно строится, `engine="greedy"`.

## Запрещено
- Вызывать LLM: маршрут считает математика.
- Писать свой VRP-алгоритм сложнее жадного — для этого есть VROOM.
- Менять приоритеты (это B4) или правила погоды (это B5).

## Общие правила (одинаковы для всех блоков)
1. **Трогай только файлы из раздела «Разрешённые пути».** Нужно изменить что-то вне списка — ОСТАНОВИСЬ и напиши владельцу этого файла. CI отклонит PR, который вышел за свои пути.
2. **Модели из `backend/app/contracts/models.py` не менять и не копировать.** Только импортировать. Не хватает поля — остановись, напиши Арсению или Некиту.
3. **Сначала уровень L0, отдельным PR.** Только после его приёмки — L1. L2 — только по прямому указанию.
4. **Переключатель уровня — переменная окружения** из раздела «Уровни». По умолчанию всегда L0. Любая ошибка L1 (сеть, ключ, таймаут, исключение) → тихий откат на L0 и запись в лог, а не падение.
5. **Внешние вызовы:** таймаут ≤ 5 с, максимум 1 повтор. В тестах сеть запрещена: тесты проходят без интернета и без ключей.
6. **Все библиотеки из раздела «Зависимости» уже установлены в каркасе** (`sentence-transformers` — extra `ml`: `uv sync --extra ml`). Файлы `pyproject.toml`, `uv.lock`, `package.json`, `bun.lock` НЕ трогай. Нужна другая библиотека — остановись и спроси.
7. **Миграции БД делает только блок D1.** Регистрацию роутов в `backend/app/api/main.py` делает только C0.
8. **Тесты обязательны** и лежат в пути из контракта. Каждый критерий приёмки = минимум один тест. Данные для тестов — только `backend/app/fixtures/demo_city.json` (не выдумывай свои).
9. **Размер PR ≤ 200 строк** без учёта тестов. Больше — дели на части.
10. Без `print`, без закомментированного кода, без TODO «на потом». Типы везде. `ruff check` чистый.

## Порядок работы
1. Попроси нейронку разбить контракт на подзадачи: сначала L0 и тесты к нему.
2. Отдай подзадачи в CLI-агент. Следи, какие файлы он меняет.
3. Запусти тесты сам. Попроси нейронку сломать реализацию и убедись, что тесты падают.
4. Открой PR и отправь отчёт в чат по шаблону ниже. Жди ревью, не начинай следующий уровень.

## Отчёт в чат
```
БЛОК: <id> · УРОВЕНЬ: L0 | L1
ВЕТКА: feat/<id>-<кратко>  →  PR в: <pair-ветка>
ИЗМЕНЁННЫЕ ФАЙЛЫ: <список>
ТЕСТЫ: <вывод pytest / tsc — последние строки>
КРИТЕРИИ ПРИЁМКИ: [x] 1  [x] 2  [ ] 3 — <почему не выполнен>
ВЫШЕЛ ЗА РАЗРЕШЁННЫЕ ПУТИ: нет | да — <что и зачем>
ВОПРОСЫ / БЛОКЕРЫ: <или «нет»>
```
