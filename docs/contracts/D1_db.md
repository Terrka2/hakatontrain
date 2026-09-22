# D1 · База данных и репозиторий

> **Контракт блока.** Вставь этот файл целиком в нейронку. Работай строго по нему.

| | |
|---|---|
| Блок | `D1` · `db` · группа LLM |
| Владелец | **Некит** |
| Запасной | Женёк |
| Первое ревью | Женёк |
| Одобряет merge | Арсений или Некит (не автор PR) |
| Ветка | `feat/D1-<кратко>` → PR в `pair/llm` |
| Зависит от | C0 |
| Кто использует | B0, B1, B5, B6, B8, D2, L3, X1 |

## Инструкция для нейронки-планировщика (ChatGPT / Qwen)
Ты — **планировщик** блока `D1`. Код ты не пишешь: код пишет CLI-агент (Antigravity / Codex / Claude Code) по твоим задачам. Человек между вами — Некит: он копирует твои задачи агенту и присылает тебе результат.

**Первый ответ.** Разбей уровень **L0** на 5–9 задач и выдай ДОСКУ (формат ниже). Требования к задаче:
- начинается с глагола, помещается в 2 строки, делается агентом за ≤ 45 минут;
- трогает только файлы из «Разрешённых путей»;
- у каждой есть **проверка** — команда или тест, по которому видно, что готово;
- первая задача — всегда тесты на критерии приёмки (они сначала красные).

**Дальше — по одной задаче.** Выдавай задачу N как готовый промпт для агента:
```
ЗАДАЧА D1-N: <что сделать>
ФАЙЛЫ: <список из разрешённых путей>
ПРОВЕРКА: <команда / тест>
НЕ ДЕЛАТЬ: <что вне этой задачи>
```
Следующую задачу давай только после моего сообщения `готово N` + вывод проверки. Проверка красная → сначала чини, задачу не закрывай. Я написал `стоп` или `блокер` → зафиксируй ❌ с причиной и предложи обход в рамках путей блока или скажи, кому написать (владелец файла, Арсений, Некит).

**Каждый твой ответ заканчивается доской целиком** — я копирую её в `docs/status/D1.md` без правок:
```
## Доска D1 · уровень L0
| # | Задача | Статус | Проверка |
|---|--------|--------|----------|
| 1 | ... | ✅ | pytest tests/blocks/... -q |
| 2 | ... | ⏳ | ... |
| 3 | ... | ☐ | ... |
Блокеры: — | <кто нужен и зачем>
Обновлено: <дата время>
```
Статусы: `☐` не начато · `⏳` в работе · `✅` проверка зелёная · `❌` блокер. Все ✅ → напиши «L0 готов, открывай PR» и выдай отчёт в чат по шаблону в конце контракта. К L1 переходи только по моему сообщению `L0 принят`.

## Цель
Единственная дверь в базу. Остальные блоки не пишут SQL и не знают, Postgres там или память.

## Разрешённые пути
Можно создавать и менять ТОЛЬКО эти файлы:
- `backend/app/db/**`
- `backend/app/alembic/versions/**`
- `backend/app/initial_data.py`
- `backend/tests/db/**`
- `docs/status/D1.md` — доска задач блока

## Порт (что блок обязан предоставить)
```python
# backend/app/db/__init__.py
class Repository(Protocol):
    def list_reports(self, *, status: str | None = None, category: str | None = None) -> list[Report]: ...
    def upsert_reports(self, reports: list[Report]) -> int: ...
    def confirm_report(self, report_id: str) -> Report: ...
    def save_clusters(self, clusters: list[Cluster], priorities: dict[str, Priority]) -> None: ...
    def list_clusters(self) -> list[tuple[Cluster, Priority | None]]: ...
    def list_events(self, start: datetime, end: datetime) -> list[Event]: ...
    def add_event(self, event: Event) -> Event: ...
    def list_infrastructure(self) -> list[InfraObject]: ...
    def list_crews(self) -> list[Crew]: ...
    def save_plan(self, plan: Plan) -> None: ...
    def get_plan(self, plan_id: str) -> Plan | None: ...
    def current_plan(self, status: str = "approved") -> Plan | None: ...     # последний с таким статусом
    def set_stop_status(self, plan_id: str, job_id: str, status: str) -> None: ...
    def add_run(self, run: OperatorRun) -> None: ...
    def list_runs(self, limit: int = 20) -> list[OperatorRun]: ...
    def set_needs_review(self, cluster_id: str, value: bool, reason: str) -> None: ...
    def reset(self) -> None: ...                     # вернуть состояние к fixture

def get_repository() -> Repository: ...             # по USE_MOCK
```

## Модели контрактов, которые использует блок
Импорт: `from app.contracts.models import ...` (фронт — типы из сгенерированного клиента). Не менять, не копировать.
```python
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


class Crew(BaseModel):
    id: str
    name: str
    skills: list[str]  # одно из SKILLS
    start: GeoPoint
    shift_start: datetime
    shift_end: datetime


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
```

## Уровни (заменяемость)
| Уровень | Что сделать |
|---|---|
| **L0** | `MemoryRepository` на `demo_city.json`. |
| **L1** | `SqlRepository`: таблицы SQLModel (в `backend/app/db/tables.py`, НЕ в `models.py` шаблона), миграция Alembic, сид из fixture в `initial_data.py`. |
| **L2** | `pgvector`: колонка эмбеддинга у обращений для D2. |

Переключатель: `USE_MOCK=true|false`

## Зависимости, которыми можно пользоваться (уже установлены)
`sqlmodel`, `alembic` (есть в шаблоне); L2: `pgvector`

## Критерии приёмки
Ссылки вида `expect.*` — это раздел `expect` в `backend/app/fixtures/demo_city.json`.
1. Один и тот же набор тестов `tests/db/test_repository.py` проходит для обеих реализаций (параметризация).
2. `reset()` возвращает ровно состояние fixture; `POST /api/v1/utils/reset` (supervisor) его вызывает.
3. `upsert_reports` дважды с теми же данными не создаёт дублей.
4. Миграция применяется на чистой БД и откатывается.

## Запрещено
- Бизнес-логика в репозитории.
- Возвращать наружу SQLModel-объекты — только модели контрактов.

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
1. Вставь этот файл целиком в чат-нейронку (ChatGPT, нет — Qwen). Она работает по «Инструкции для планировщика» и выдаёт доску задач.
2. Копируй задачи по одной в CLI-агент. Смотри diff: файл вне «Разрешённых путей» — откати.
3. Запусти проверку из задачи сам, пришли вывод планировщику: `готово N` + вывод. Доску из ответа сохрани в `docs/status/<ID>.md` и закоммить вместе с кодом.
4. Все ✅ → попроси нейронку сломать реализацию и убедись, что тесты падают. Открой PR, отправь отчёт в чат по шаблону ниже. Следующий уровень — только после `L0 принят`.

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
