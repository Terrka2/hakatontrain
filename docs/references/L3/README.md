# Референсы L3 · Инструменты оператора и MCP-сервер

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/backend_block/`
- `docs/references/_patterns/llm_call/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
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

Переключатель уровня: `MCP=off|on`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `backend/app/blocks/tools/**`
- `backend/app/mcp_server.py`
- `backend/tests/blocks/tools/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. `call` с ролью не из `Tool.roles` → `PermissionError`, инструмент не выполнен, отказ записан в журнал.
2. `approve_plan` через `call` → `PendingAction`, план остаётся `draft`; `execute_pending` от supervisor → `approved`.
3. `rebuild_plan` выполняется без подтверждения и возвращает план со `status="draft"`.
4. Аргументы, не прошедшие `args_schema` → `ValidationError`, инструмент не выполнен.
5. MCP-сервер отдаёт список инструментов, совпадающий с `REGISTRY` (тест через in-memory клиент `mcp`, без сети).
6. Ни один инструмент не обращается к LLM и к интернету.
