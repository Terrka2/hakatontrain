# Референсы C0 · Каркас проекта

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`
- `docs/references/_patterns/frontend_feature/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
Результат — не функция, а состояние репозитория:
- шаблон импортирован, `docker compose up` поднимает backend + frontend + postgres + mailpit;
- `backend/app/contracts/models.py` и `backend/app/fixtures/demo_city.json` сохранены как есть;
- для КАЖДОГО backend-блока создан пакет `backend/app/blocks/<name>/__init__.py` с функциями из его контракта, которые бросают `NotImplementedError`;
- для каждого роутера создан файл `backend/app/api/routes/<name>.py` с пустым `router = APIRouter(prefix=..., tags=[...])`, и ВСЕ роутеры уже подключены в `backend/app/api/main.py`;
- `backend/app/core/config.py` содержит все переключатели уровней: `USE_MOCK, ROUTER, NAV, EMBEDDER, LLM, WEATHER, OPTIONAL_BLOCKS` со значениями L0 по умолчанию;
- `frontend/src/features/<name>/index.ts` создан для F1–F5; пункты меню и маршруты-заглушки добавлены; меню зависит от роли;
- `frontend/src/mocks/demo_city.json` — копия backend-fixture (скрипт `scripts/sync_fixture.sh`).

Переключатель уровня: —. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/**`
- `frontend/**`
- `compose*.yml`
- `docker-compose*.yml`
- `.env.example`
- `README.md`
- `.github/workflows/**`
- `scripts/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. `docker compose up` с чистого клона поднимает стек; `/docs` открывается.
2. `pytest` зелёный (тесты шаблона + `tests/test_fixture_valid.py`, который загружает fixture через модели контрактов).
3. Регистрация/логин/восстановление пароля из шаблона работают; письма видны в Mailpit.
4. `grep -r NotImplementedError backend/app/blocks` показывает гнездо для каждого блока B0–B6, B8, D2, L1–L3 (дополнительные B7, X1 — тоже, они выключены флагом `OPTIONAL_BLOCKS=off`).
5. Засеяны демо-пользователи: `supervisor@demo.md` (руководитель) и `crew1@demo.md`, `crew2@demo.md`, `crew3@demo.md` (бригады c1–c3). Роль — поле `role` у User (`supervisor | crew | citizen`), у бригадира ещё `crew_id`.
