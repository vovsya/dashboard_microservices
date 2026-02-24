from fastapi import APIRouter, HTTPException, Depends, Path, Body, Query
from dashboard_app.dashboard.security.auth import get_current_user
from sqlalchemy import text
from dashboard_app.dashboard.db.db_engine import engine
from dashboard_app.dashboard.utils.apicalls import get_weather, get_currencies
from datetime import date, datetime
import random


pages_router = APIRouter(prefix="/pages", tags=["Страницы"])


@pages_router.post("/creation")
async def page_creation(
    current_user_id=Depends(get_current_user),
    page: int = Query(..., description="Придумайте номер новой страницы"),
):
    async with engine.begin() as conn:
        update = await conn.execute(
            text(
                """
                INSERT INTO pages (user_id, page)
                SELECT id, :page FROM USERS
                WHERE id = :id
                ON CONFLICT (user_id, page) DO NOTHING
                """
            ),
            {"id": current_user_id, "page": page},
        )

        if update.rowcount == 0:
            raise HTTPException(status_code=409, detail="Невозможно добавить страницу")

    return {"Страница": "добавлена"}


@pages_router.delete("/deletion")
async def page_deletion(
    page: int = Body(..., description="Введите номер страницы"),
    current_user_id=Depends(get_current_user),
):
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                """
                DELETE FROM pages
                WHERE page = :page AND user_id = :user_id
                """
            ),
            {"page": page, "user_id": current_user_id},
        )

        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Страницы не сущетсвуте")

    return {"Страница": "Удалена"}


@pages_router.get("/{page}")
async def view_page(
    page: int = Path(..., description="Номер страницы"),
    current_user_id: int = Depends(get_current_user),
):
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                """
                SELECT nickname, weather, time, date, traffic, currencies, todo, diet, site_monitoring
                FROM pages
                WHERE page = :page AND user_id = :user_id
                """
            ),
            {"page": page, "user_id": current_user_id},
        )

        page_widgets = {}
        res = res.mappings().first()

        if res is None:
            raise HTTPException(status_code=404, detail="Страница не найдена или пользователь не существует")

        if res["nickname"]:
            nickname = await conn.execute(
                text(
                    """
                    SELECT username FROM users
                    WHERE id = :id
                    """
                ),
                {"id": current_user_id},
            )
            nickname = nickname.scalar_one_or_none()
            page_widgets["Имя пользователя"] = nickname

        if res["todo"]:
            todos = await conn.execute(
                text(
                    """
                    SELECT number, task FROM todos
                    WHERE user_id = :user_id AND date = :today
                    """
                ),
                {"user_id": current_user_id, "today": date.today()},
            )

            todos = todos.mappings().all()
            if todos:
                page_widgets["Задачи"] = todos

        if res["diet"]:
            diet = await conn.execute(
                text(
                    """
                    SELECT breakfast, lunch, dinner FROM diets
                    WHERE date = :today AND user_id = :user_id
                    """
                ),
                {"user_id": current_user_id, "today": date.today()},
            )

            diet = diet.mappings().first()
            if diet:
                page_widgets["Рацион"] = dict(diet)

        if res["site_monitoring"]:
            monitors = await conn.execute(
                text(
                    """
                    SELECT url, interval_minutes, registration_status,
                           last_status, last_checked_at, last_changed, last_error
                    FROM site_monitors
                    WHERE user_id = :user_id
                    ORDER BY url
                    """
                ),
                {"user_id": current_user_id},
            )
            monitors = [dict(r) for r in monitors.mappings().all()]
            if monitors:
                page_widgets["Мониторинг сайтов"] = monitors

    if res["weather"]:
        page_widgets["Погода"] = await get_weather()

    if res["time"]:
        page_widgets["Время"] = datetime.now().time()

    if res["date"]:
        page_widgets["Дата"] = datetime.now().date()

    if res["traffic"]:
        page_widgets["Пробки"] = str(random.randint(1, 10)) + " баллов"

    if res["currencies"]:
        page_widgets["Курсы валют"] = await get_currencies()

    return page_widgets


@pages_router.put("/{page}")
async def clear_page(
    page: int = Path(..., description="Номер страницы"),
    current_user_id: int = Depends(get_current_user),
):
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                UPDATE pages
                SET
                    nickname =       FALSE,
                    todo =           FALSE,
                    diet =           FALSE,
                    weather =        FALSE,
                    "time" =        FALSE,
                    "date" =        FALSE,
                    traffic =        FALSE,
                    currencies =     FALSE,
                    site_monitoring = FALSE
                WHERE user_id = :user_id AND page = :page
                """
            ),
            {"user_id": current_user_id, "page": page},
        )

    return {"Страница": "очищена"}
