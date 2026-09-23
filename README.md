# CityTriage

ИИ-оператор городских служб: сам разбирает обращения, склеивает дубликаты, объясняет приоритет и собирает бригадам маршруты. Руководитель утверждает план, бригада работает с телефона.

**Сначала прочитай:** [концепт](docs/CONCEPT.md) · [карта блоков и статус](docs/BLOCKS.md) · [как мы работаем](docs/WORKFLOW.md) · свой контракт в [docs/contracts/](docs/contracts/).
AI-агентам: правила в [AGENTS.md](AGENTS.md).

## Запуск

Нужны: [uv](https://docs.astral.sh/uv/), [bun](https://bun.sh), Docker.

```bash
cp .env.example .env && cp frontend/.env.example frontend/.env
uv sync                      # backend-зависимости (Python 3.14 uv скачает сам)
bun install                  # frontend-зависимости
```

**Вариант А — всё в Docker:**
```bash
docker compose up --build    # сайт и API :8000 · postgres :5432 · Mailpit :8025
```

Перед запуском API сервис `prestart` применяет миграции и создаёт демо-пользователей.
Фронтенд собирается в backend-образ и доступен на http://localhost:8000;
Swagger — http://localhost:8000/docs. Для отслеживания изменений: `docker compose watch`.

**Вариант Б — локально, в Docker только база и почта:**
```bash
docker compose up -d db mailpit
cd backend && uv run alembic upgrade head && uv run python app/initial_data.py
uv run fastapi dev app/main.py          # http://localhost:8000/docs
cd frontend && bun run dev              # http://localhost:5173
```

## Демо-пользователи
Пароль у всех — `DEMO_PASSWORD` из `.env` (по умолчанию `demo-citytriage`).

| Email | Роль |
|---|---|
| `supervisor@demo.md` | руководитель службы |
| `crew1@demo.md`, `crew2@demo.md`, `crew3@demo.md` | бригадиры (бригады c1–c3) |
| `admin@example.com` / `FIRST_SUPERUSER_PASSWORD` | администратор |

## Проверки перед PR
```bash
cd backend && uv run ruff check app tests && uv run pytest -q     # API-тестам нужна запущенная база
cd backend && uv run pytest tests/blocks tests/test_fixture_valid.py -q   # тесты блоков — без базы и сети
cd frontend && bun run lint && bun run build
python3 scripts/check_paths.py <ID блока>                          # не вышел ли за свои пути
```
После изменения API: `bash scripts/generate-client.sh` — пересобирает типизированный клиент фронта (делает Арсений).

## Уровни блоков
Каждый блок имеет L0 (заглушка на fixture) → L1 (целевой) → L2. Переключатели — в `.env`:
`USE_MOCK, ROUTER, NAV, EMBEDDER, LLM, WEATHER, GEOCODER, MCP, OPTIONAL_BLOCKS`. По умолчанию всё на L0.

Каркас: [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) (MIT, см. `THIRD_PARTY/`).
