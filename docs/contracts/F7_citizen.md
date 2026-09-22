# F7 · Экран жителя (дополнительный)

> **Контракт блока.** Вставь этот файл целиком в нейронку. Работай строго по нему.

| | |
|---|---|
| Блок | `F7` · `citizen` · группа OPTIONAL |
| Владелец | **Арсений** |
| Запасной | Женёк |
| Первое ревью | Некит |
| Одобряет merge | Арсений или Некит (не автор PR) |
| Ветка | `feat/F7-<кратко>` → PR в `pair/frontend` |
| Зависит от | F1, F6, B7, B1, X1 |
| Кто использует | — |

## Цель
Житель строит маршрут, видит проблемы и мероприятия по пути, подтверждает «всё ещё там» и может сообщить о новой проблеме.

## Разрешённые пути
Можно создавать и менять ТОЛЬКО эти файлы:
- `frontend/src/features/citizen/**`
- `frontend/src/routes/_layout/trip.tsx`
- `frontend/src/routes/_layout/events.tsx`
- `frontend/src/routes/_layout/report.tsx`

## Порт (что блок обязан предоставить)
```tsx
export function TripPlanner(): JSX.Element        // A и B кликом по карте или адресом → Trip
export function HazardList(props: { hazards: HazardOnRoute[]; onConfirm: (clusterId: string) => void }): JSX.Element
export function EventsList(props: { items: Event[] }): JSX.Element
export function ReportForm(): JSX.Element         // категория, текст, точка на карте, фото
```

## Модели контрактов, которые использует блок
Импорт: `from app.contracts.models import ...` (фронт — типы из сгенерированного клиента). Не менять, не копировать.
```python
class TripRequest(BaseModel):
    origin: GeoPoint
    destination: GeoPoint
    depart_at: datetime | None = None


class Trip(BaseModel):
    """Маршрут жителя A→B с проблемами и мероприятиями по пути."""

    geometry: list[GeoPoint]
    duration_min: float
    distance_m: float
    hazards: list[HazardOnRoute] = []
    events: list[Event] = []
    engine: str = "straight"  # "straight" | "ors"


class HazardOnRoute(BaseModel):
    cluster_id: str
    category: str
    priority: float
    location: GeoPoint
    distance_from_start_m: float


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
| **L0** | Mock-маршрут с проблемами по пути; список мероприятий. |
| **L1** | `POST /trips`, «Всё ещё там» → `POST /reports/{id}/confirm`, форма → `POST /reports`. |
| **L2** | Сохранённые поездки и напоминания; лидерборд подтверждений. |

Переключатель: `VITE_USE_MOCK`, `OPTIONAL_BLOCKS`

## Зависимости, которыми можно пользоваться (уже установлены)
—

## Критерии приёмки
Ссылки вида `expect.*` — это раздел `expect` в `backend/app/fixtures/demo_city.json`.
1. Маршрут через центр показывает яму `r012` и событие `e1` (на дату 27.09).
2. «Всё ещё там» увеличивает счётчик; после прохода оператора приоритет кластера вырос.
3. Роль citizen не видит экранов руководителя и бригады.
4. Удобно на 390 px.

## Запрещено
- Отдельное мобильное приложение.

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
