from fastapi import APIRouter

from app.api.routes import (
    assistant,
    clusters,
    context,
    crew,
    events,
    login,
    operator,
    plan,
    private,
    reports,
    search,
    trips,
    users,
    utils,
)
from app.core.config import settings

# ЗАМОРОЖЕНО после C0: все роутеры блоков уже подключены. Блоки наполняют свои файлы в routes/.
api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(reports.router)
api_router.include_router(clusters.router)
api_router.include_router(operator.router)
api_router.include_router(context.router)
api_router.include_router(plan.router)
api_router.include_router(crew.router)
api_router.include_router(search.router)
api_router.include_router(assistant.router)

# Дополнительные блоки (B7 навигатор, X1 мероприятия) — только по флагу.
if settings.OPTIONAL_BLOCKS == "on":
    api_router.include_router(trips.router)
    api_router.include_router(events.router)

if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
