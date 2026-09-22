# X1 · Мероприятия (дополнительный)

> **Контракт блока.** Вставь этот файл целиком в нейронку. Работай строго по нему.

| | |
|---|---|
| Блок | `X1` · `events` · группа OPTIONAL |
| Владелец | **Пашок** |
| Запасной | Некит |
| Первое ревью | Женёк |
| Одобряет merge | Арсений или Некит (не автор PR) |
| Ветка | `feat/X1-<кратко>` → PR в `pair/backend` |
| Зависит от | B2, B5, D1 |
| Кто использует | B4, B6, B7 |

## Цель
Городские мероприятия как сигнал для оператора: проблема на месте будущего забега важнее и должна быть закрыта до его начала.

## Разрешённые пути
Можно создавать и менять ТОЛЬКО эти файлы:
- `backend/app/blocks/events/**`
- `backend/app/api/routes/events.py`
- `backend/app/blocks/priority/factors/ex.py`
- `backend/tests/blocks/events/**`

## Порт (что блок обязан предоставить)
```python
# backend/app/blocks/events/__init__.py
def get_events(start: datetime, end: datetime) -> list[Event]: ...
def enrich_context(ctx: Context) -> Context: ...                                   # добавляет ctx.events
def apply_deadlines(jobs: list[Job], clusters: list[Cluster], events: list[Event]) -> tuple[list[Job], list[Decision]]: ...
```
- фактор `EX` (файл `priority/factors/ex.py`): кластер в радиусе события, начинающегося ≤ 72 ч → `min(1, expected_people / 1000)`, иначе 0; нет событий → `None`;
- `apply_deadlines`: задача в радиусе события, начинающегося ≤ 72 ч → `deadline = event.starts_at`, `Decision.kind="deadline"`.
Роуты (`/api/v1/events`): `GET /events?from=&to=`, `POST /events` (supervisor).

## Модели контрактов, которые использует блок
Импорт: `from app.contracts.models import ...` (фронт — типы из сгенерированного клиента). Не менять, не копировать.
```python
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


class Context(BaseModel):
    """Всё внешнее, что влияет на решения. Собирает блок B5."""

    now: datetime
    weather: Weather | None = None
    events: list[Event] = []
    infrastructure: list[InfraObject] = []


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
```

## Уровни (заменяемость)
| Уровень | Что сделать |
|---|---|
| **L0** | Событие `e1` из fixture. |
| **L1** | События из БД, ручной ввод руководителем. |
| **L2** | Один внешний источник из allowlist (API/RSS, не скрейпинг HTML). |

Переключатель: `OPTIONAL_BLOCKS=on|off`

## Зависимости, которыми можно пользоваться (уже установлены)
—

## Критерии приёмки
Ссылки вида `expect.*` — это раздел `expect` в `backend/app/fixtures/demo_city.json`.
1. `get_events` возвращает `e1` для 26–28 сентября 2026 и пусто для октября.
2. Задачи по `r012` и `r013` получают `deadline = начало e1` (`expect_optional.event_deadline_reports`).
3. Фактор `EX` для кластера `r012` = 1.0, в `evidence` назван забег; для `r001` = 0.
4. `OPTIONAL_BLOCKS=off` → `ctx.events == []`, роуты отдают 404, ядро работает как раньше.

## Запрещено
- Менять другие файлы блока B4, кроме `factors/ex.py`.
- Скрейпинг произвольных сайтов.

## Примечание
ДОПОЛНИТЕЛЬНЫЙ БЛОК. Не начинать, пока Арсений явно не скажет.

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
