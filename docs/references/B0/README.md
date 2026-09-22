# Референсы B0 · ИИ-оператор: самостоятельный проход

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/operator/__init__.py
class PipelineResult(BaseModel):
    clusters: list[Cluster]
    priorities: dict[str, Priority]   # cluster_id -> Priority
    context: Context

def run_pipeline(reports: list[Report], now: datetime) -> PipelineResult: ...
def operator_run(trigger: str, now: datetime, job_update: JobUpdate | None = None) -> OperatorRun: ...
```
Порядок шагов `operator_run` фиксирован (это и есть «детерминированная нейронка»):
`загрузить обращения → L1 extract+verify → B3 clusters → B5 context → B4 priority → B6 make_jobs → B6 solve | replan → сохранить черновик плана → записать OperatorRun`
- `trigger="job_update"` → вместо `solve` вызывается `B6.replan(...)`;
- `summary` заполняется шаблоном: «Разобрано N обращений → M проблем (K новых). На проверку: … . План v3: … ». Красивый текст поверх — дело L2;
- оператор НИКОГДА не ставит `Plan.status="approved"`.

Роуты:
- `GET /api/v1/clusters?sort=priority&category=&min_score=` → `list[ClusterOut]` (Cluster + Priority)
- `GET /api/v1/clusters/{id}` → Cluster + Priority + `reports: list[Report]`
- `POST /api/v1/clusters/{id}/review {decision: "accept"|"reject"}` (supervisor) — снять `needs_review`
- `GET /api/v1/operator/runs?limit=` → лента `list[OperatorRun]`, новые сверху
- `POST /api/v1/operator/run {trigger}` (supervisor) — запустить проход вручную

Переключатель уровня: `USE_MOCK=true|false`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/operator/**`
- `backend/app/api/routes/clusters.py`
- `backend/app/api/routes/operator.py`
- `backend/tests/blocks/operator/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. На fixture `GET /clusters` возвращает ровно `expect.clusters` кластеров; первые два по баллу содержат `r001` и `r011`.
2. У каждого кластера в ответе непустой `factors[]`; кластер `r006` приходит с `needs_review=true`.
3. `operator_run("manual")` возвращает `OperatorRun` с `clusters_total=13`, `needs_review` содержит кластер `r006`, `plan_id` указывает на план со `status="draft"`.
4. Два вызова подряд на одних данных → одинаковые кластеры, баллы и маршруты (детерминированность).
5. Блок B4 или B6 бросил исключение → проход не падает: кластеры отданы, в `decisions` запись об ошибке, `plan_id=None`.
6. `POST /clusters/{id}/review accept` для `r006` → следующий проход включает его в план.
