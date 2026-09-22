# L3 · Инструменты оператора и MCP-сервер

> **Контракт блока.** Вставь этот файл целиком в нейронку. Работай строго по нему.

| | |
|---|---|
| Блок | `L3` · `tools` · группа LLM |
| Владелец | **Некит** |
| Запасной | Женёк |
| Первое ревью | Арсений |
| Одобряет merge | Арсений или Некит (не автор PR) |
| Ветка | `feat/L3-<кратко>` → PR в `pair/llm` |
| Зависит от | B0, B5, B6, B8, D1, D2 |
| Кто использует | L2 |

## Цель
Закрытый список действий, доступных нейронке. Вся математика проекта (дубликаты, приоритет, маршруты, перестройка) видна модели ТОЛЬКО как инструменты. Те же инструменты опубликованы как MCP-сервер — к оператору можно подключить любой внешний MCP-клиент.

## Разрешённые пути
Можно создавать и менять ТОЛЬКО эти файлы:
- `backend/app/blocks/tools/**`
- `backend/app/mcp_server.py`
- `backend/tests/blocks/tools/**`

## Порт (что блок обязан предоставить)
```python
# backend/app/blocks/tools/__init__.py
class Tool(BaseModel):
    name: str
    description: str
    args_schema: type[BaseModel]
    writes: bool
    requires_human: bool          # True → только PendingAction, выполняет человек-supervisor
    roles: list[str]              # supervisor | crew

REGISTRY: dict[str, Tool]

def call(name: str, args: dict, role: str, actor: str) -> BaseModel | PendingAction: ...
def execute_pending(action: PendingAction, role: str, actor: str) -> BaseModel: ...
```
| Инструмент | Пишет | Нужен человек | Роли |
|---|---|---|---|
| `get_cluster`, `explain_priority`, `search`, `get_context`, `list_runs`, `get_plan`, `crew_progress` | нет | нет | supervisor |
| `my_route` | нет | нет | crew |
| `run_operator(trigger)`, `rebuild_plan`, `set_weather_scenario` | да | **нет** — оператор делает сам, результат всегда черновик | supervisor |
| `report_job(JobUpdate)` | да | нет | crew |
| `approve_plan(plan_id)`, `review_cluster(id, decision)` | да | **да** | supervisor |

Каждый вызов (и отказ) пишется в журнал `backend/app/blocks/tools/audit.py`: кто, роль, инструмент, аргументы, результат, время.

## Модели контрактов, которые использует блок
Импорт: `from app.contracts.models import ...` (фронт — типы из сгенерированного клиента). Не менять, не копировать.
```python
class PendingAction(BaseModel):
    """Действие, которое ИИ-оператор сам выполнить не вправе: ждёт решения руководителя."""

    id: str
    tool: str  # имя write-инструмента
    args: dict[str, Any]
    summary: str  # что именно будет сделано, человеческим языком


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


class CrewRoute(BaseModel):
    crew_id: str
    stops: list[RouteStop]
    geometry: list[GeoPoint] = []  # линия для карты
    drive_min: int = 0
    work_min: int = 0


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


class Priority(BaseModel):
    cluster_id: str
    score: float = Field(ge=0, le=100)
    factors: list[Factor]
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = False


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
```

## Уровни (заменяемость)
| Уровень | Что сделать |
|---|---|
| **L0** | Реестр + инструменты чтения; вызывают порты блоков (`__init__`), не HTTP. |
| **L1** | Инструменты записи, `PendingAction`, журнал. **MCP-сервер** `backend/app/mcp_server.py` на официальном `mcp` SDK (FastMCP) поверх того же `REGISTRY`: каждый `Tool` → MCP tool со схемой из `args_schema`; `requires_human` инструменты по MCP возвращают `PendingAction`, а не выполняются. |
| **L2** | Авторизация MCP-клиента по токену и роли. |

Переключатель: `MCP=off|on`

## Зависимости, которыми можно пользоваться (уже установлены)
`mcp`

## Критерии приёмки
Ссылки вида `expect.*` — это раздел `expect` в `backend/app/fixtures/demo_city.json`.
1. `call` с ролью не из `Tool.roles` → `PermissionError`, инструмент не выполнен, отказ записан в журнал.
2. `approve_plan` через `call` → `PendingAction`, план остаётся `draft`; `execute_pending` от supervisor → `approved`.
3. `rebuild_plan` выполняется без подтверждения и возвращает план со `status="draft"`.
4. Аргументы, не прошедшие `args_schema` → `ValidationError`, инструмент не выполнен.
5. MCP-сервер отдаёт список инструментов, совпадающий с `REGISTRY` (тест через in-memory клиент `mcp`, без сети).
6. Ни один инструмент не обращается к LLM и к интернету.

## Запрещено
- Инструмент «выполни произвольный SQL / HTTP / код».
- Инструмент, который ставит `approved` без человека.
- Дублировать логику блоков внутри инструментов.

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
