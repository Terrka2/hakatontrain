# F2 · Очередь приоритетов и карточка проблемы

> **Контракт блока.** Вставь этот файл целиком в нейронку. Работай строго по нему.

| | |
|---|---|
| Блок | `F2` · `queue` · группа FRONTEND |
| Владелец | **Арсений** |
| Запасной | Дорофей |
| Первое ревью | Некит |
| Одобряет merge | Арсений или Некит (не автор PR) |
| Ветка | `feat/F2-<кратко>` → PR в `pair/frontend` |
| Зависит от | F1, F6, B0 |
| Кто использует | — |

## Цель
Экран оператора: что чинить первым и ПОЧЕМУ. Главный экран для судей по критерию «объяснимость».

## Разрешённые пути
Можно создавать и менять ТОЛЬКО эти файлы:
- `frontend/src/features/queue/**`
- `frontend/src/routes/_layout/queue.tsx`

## Порт (что блок обязан предоставить)
```tsx
export function PriorityQueue(props: { items: ClusterOut[]; selectedId?: string; onSelect: (id: string) => void }): JSX.Element
export function ClusterCard(props: { cluster: ClusterOut; reports: Report[] }): JSX.Element
export function PriorityBar(props: { factors: Factor[]; score: number }): JSX.Element
```
`PriorityBar` — горизонтальная полоса, сегмент на фактор, ширина = `points`; под ней список «+23 Опасность — открытый люк; ребёнок чуть не упал». Факторы с `score=null` показаны серым «нет данных».
`ClusterCard`: исходные обращения (язык, фото, подтверждения), для пар — «почему склеено: 25 м, сходство 0.71», бейдж `needs_review` с причинами и кнопки руководителя «Принять / Отклонить» (`POST /clusters/{id}/review`).

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


class Factor(BaseModel):
    """Вклад одного фактора в приоритет. Из этого фронт рисует PriorityBar."""

    code: str  # HZ DM AG SP RC EX WX VF
    label: str  # человекочитаемо, на русском
    score: float | None  # 0..1; None = данных нет, фактор исключён из суммы
    weight: float
    points: float  # вклад в итоговые 0..100
    evidence: list[str] = []


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


class Verification(BaseModel):
    """Проверка на «нейрослоп» и неправдоподобные обращения (блок L1)."""

    status: Literal["unverified", "plausible", "suspicious", "confirmed"] = "unverified"
    reasons: list[str] = []
    confidence: float = Field(default=0.0, ge=0, le=1)
```

## Уровни (заменяемость)
| Уровень | Что сделать |
|---|---|
| **L0** | Список + карточка + PriorityBar на mock. |
| **L1** | Реальный API, фильтры по категории/статусу, синхронизация выбора с картой. |
| **L2** | Ползунки весов с мгновенным пересчётом очереди. |

Переключатель: `VITE_USE_MOCK`

## Зависимости, которыми можно пользоваться (уже установлены)
—

## Критерии приёмки
Ссылки вида `expect.*` — это раздел `expect` в `backend/app/fixtures/demo_city.json`.
1. Клик по строке очереди центрирует карту и открывает карточку; клик по маркеру выделяет строку.
2. Сумма подписей сегментов PriorityBar = балл.
3. Кластер `r006` виден с бейджем «требует проверки».
4. На 390 px очередь и карточка читаемы без горизонтального скролла.

## Запрещено
- Считать что-либо на фронте — только показывать то, что пришло из API.
- Свои цвета и отступы мимо токенов F6.

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
