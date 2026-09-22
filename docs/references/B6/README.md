# Референсы B6 · Диспетчер: план и маршруты бригад

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
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

Переключатель уровня: `ROUTER=greedy|vroom`, `ORS_API_KEY`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/dispatch/**`
- `backend/app/api/routes/plan.py`
- `backend/tests/blocks/dispatch/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
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
