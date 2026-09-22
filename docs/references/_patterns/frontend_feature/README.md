# Образец frontend-фичи

Раскладка (имя `queue` заменяется на `name` блока из контракта):
```
frontend/src/features/queue/index.ts        публичный интерфейс фичи: только то, что экспортировано здесь
frontend/src/features/queue/api.ts          данные: mock из src/mocks/demo_city.json ↔ реальный API, переключатель VITE_USE_MOCK
frontend/src/features/queue/useQueue.ts     хук на TanStack Query поверх api.ts
frontend/src/features/queue/QueueScreen.tsx экран: только компоненты из components/ui и токены темы, без #hex
frontend/src/routes/_layout/queue.tsx       маршрут уже создан C0: заменить BlockPlaceholder на QueueScreen
```
- Типы ответов API — из сгенерированного клиента `@/client` (после `bun run generate-client`), свои дубликаты типов не заводить.
- Цвета приоритета, бригад, статусов — только из `@/theme/priority` (блок F6). В `features/**` нет `#hex` и `rgb(` — CI проверяет grep-ом.
- Роль пользователя — из `useAuth()`; экран не показывает то, что роли не положено.
