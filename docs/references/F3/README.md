# Референсы F3 · Пульт руководителя: лента оператора, план, утверждение

> **Референсы фиксированы.** Агент пишет код в стиле и структуре этих файлов и не предлагает свою архитектуру, другие библиотеки, другую раскладку файлов. Расхождение референса с контрактом — контракт главнее; напиши об этом в отчёте. Папку `docs/references/` менять нельзя.

## Какие образцы применять
- `docs/references/_patterns/frontend_feature/`

## Что зафиксировано контрактом (не обсуждается)
Порт блока (сигнатуры — из контракта, реализация — по образцу):
```tsx
export function OperatorFeed(props: { runs: OperatorRun[] }): JSX.Element          // «07:02 · импорт · 16 обращений → 13 проблем, 1 на проверку, план v1»
export function PlanView(props: { plan: Plan; crews: Crew[] }): JSX.Element        // колонки по бригадам: остановки, время, статус
export function PlanDiff(props: { current: Plan | null; draft: Plan }): JSX.Element // что изменилось: добавлено / убрано / переехало к другой бригаде
export function DecisionLog(props: { decisions: Decision[] }): JSX.Element
export function PlanVsBaseline(props: { total: number; baseline: number }): JSX.Element
export function ApproveBar(props: { draft: Plan; onApprove: () => void }): JSX.Element
```
Кнопки демо: переключатель погоды «Ясно / Шторм», «Сброс демо». Ленту и черновик опрашивать каждые 5 с (TanStack Query `refetchInterval`).

Переключатель уровня: `VITE_USE_MOCK`. По умолчанию L0. Ошибка L1 → откат на L0 + запись в лог.

## Куда смотреть в каркасе
- `frontend/src/features/dispatch/**`
- `frontend/src/routes/_layout/plan.tsx`

## Данные для тестов
Только `backend/app/fixtures/demo_city.json` (фронт — `frontend/src/mocks/demo_city.json`, копия). Эталон — раздел `expect`. Критерии приёмки, которые должны стать тестами:
1. После «Сброс демо» и прохода оператора виден черновик v1: маршруты трёх бригад разными цветами.
2. Остановка с несколькими кластерами показана как «4 проблемы · 1 выезд».
3. «Утвердить» доступна только роли supervisor; после нажатия статус плана «Отправлен бригадам».
4. Бригада отметила «не могу» → в течение 5–10 с в ленте новая запись, появляется черновик v2 и `PlanDiff` с изменениями.
5. Переключение на «Шторм» → новый черновик; отложенные ямы видны в журнале с причиной.
