# Референсы L2 · LLM: ассистент-диспетчер на фиксированном графе

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`
- `docs/references/_patterns/llm_call/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```python
# backend/app/blocks/assistant/__init__.py
Intent = Literal["what_happened", "explain_priority", "explain_plan", "find_similar", "crew_status",
                 "rebuild_plan", "set_weather", "review_cluster", "approve_plan", "my_route", "report_job",
                 "smalltalk", "unknown"]

def handle(req: AssistantRequest) -> AssistantResponse: ...
def confirm(session_id: str, pending_id: str, approve: bool) -> AssistantResponse: ...
def narrate(run: OperatorRun) -> str: ...        # человеческий текст для ленты оператора; LLM=off → run.summary как есть
```
Граф (LangGraph `StateGraph`), узлы фиксированы:
`classify_intent → check_role → gather_context(ui_state) → call_tool → [needs_confirmation?] → compose_answer`
- `check_role`: таблица «роль → разрешённые intent». supervisor — всё; crew — только `my_route`, `report_job`, `explain_plan`, `smalltalk`.
- `gather_context`: так ассистент «видит карту» — берёт `ui_state.selected_cluster_id`, `bbox`, `filters`.
- `call_tool`: ровно один инструмент из L3 на intent; параметры — структурированный вывод по схеме инструмента.
- инструменты с `requires_human=True` (утвердить план, отклонить обращение) возвращают `PendingAction` и выполняются только через `confirm(...)` человеком-supervisor; остальные оператор выполняет сам и пишет в журнал.
- `compose_answer`: текст пишет LLM, но ТОЛЬКО по результату инструмента; числа берутся из результата, не из головы модели.
- `trace` содержит пройденные узлы.
Роуты: `POST /api/v1/assistant/message`, `POST /api/v1/assistant/confirm`, `GET /api/v1/assistant/narrate/{run_id}` → текст для ленты (блок B0 сам L2 не вызывает — иначе цикл зависимостей).

Переключатель уровня: `LLM=off|on`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/assistant/**`
- `backend/app/api/routes/assistant.py`
- `backend/tests/blocks/assistant/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. «что ты сделал за утро?» → `what_happened`: ответ построен по последним `OperatorRun`, числа совпадают с лентой.
2. «почему эта яма первая?» при выбранном кластере → `explain_priority`, названы топ-3 фактора ИЗ `Priority.factors`.
3. «пошёл ливень» → `set_weather(storm)` выполнен сразу (человек не нужен), оператор перестроил черновик; в ответе перечислено, что отложено, и `actions` содержит `show_plan`.
4. «утверди план» от supervisor → `pending` заполнен, план остаётся `draft` до `confirm`; после `confirm` — `approved`.
5. «утверди план» от crew → отказ, инструмент НЕ вызван (проверяется по `trace`).
6. «что у меня дальше?» от crew1 → `my_route`, следующая `pending`-остановка бригады c1.
7. Одинаковый запрос дважды при `LLM=off` → одинаковый `trace` и одинаковый результат инструмента.
8. `narrate(run)` при `LLM=on` не содержит чисел, которых нет в `run`. Непонятный запрос → `unknown` и список умений.
