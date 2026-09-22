# Референсы F4 · Панель ассистента

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/frontend_feature/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```tsx
export function AssistantDrawer(): JSX.Element
export function applyUiActions(actions: UIAction[]): void      // focus_cluster / show_plan / show_run / show_crew / set_filter
export function ConfirmCard(props: { pending: PendingAction; onDecide: (approve: boolean) => void }): JSX.Element
```

Переключатель уровня: `VITE_USE_MOCK`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `frontend/src/features/assistant/**`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. Сообщение уходит с текущим `selected_cluster_id` и `bbox`.
2. Ответ с `show_plan` открывает экран плана; с `focus_cluster` — центрирует карту.
3. При `pending` показана карточка подтверждения; без нажатия «Подтвердить» запрос `confirm` не уходит.
4. Ошибка/таймаут API → понятное сообщение в панели, приложение работает дальше.
