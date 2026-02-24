from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from dashboard_app.dashboard.routes.pages import pages_router
from dashboard_app.dashboard.routes.profile import profile_router
from dashboard_app.dashboard.routes.widgets import widgets_router
from dashboard_app.dashboard.utils.site_monitoring_streams import (
    startup_sitewatch_consumer,
    shutdown_sitewatch_consumer,
)


dashboard_app = FastAPI(
    title="Дашборд-приложение async FastAPI+PostgreSQL https://github.com/vovsya/dashboard_project",
    description="Вы можете создавать странички и добавлять на них виджеты - Погода и курсы валют изменяются в реальном времени",
)


dashboard_app.include_router(pages_router)
dashboard_app.include_router(profile_router)
dashboard_app.include_router(widgets_router)


@dashboard_app.on_event("startup")
async def _startup_streams() -> None:
    await startup_sitewatch_consumer()


@dashboard_app.on_event("shutdown")
async def _shutdown_streams() -> None:
    await shutdown_sitewatch_consumer()


@dashboard_app.get("/", tags=["Корень"])
def root():
    return RedirectResponse(url="/docs")
