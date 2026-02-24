from datetime import date

from fastapi import APIRouter, HTTPException, Body, Depends, Path, Form
from sqlalchemy import text

from dashboard_app.dashboard.schemas.classes import WidgetChoice, Choice
from dashboard_app.dashboard.db.db_engine import engine
from dashboard_app.dashboard.security.auth import get_current_user
from dashboard_app.dashboard.utils.site_monitoring_streams import publish_register_monitor_command

widgets_router = APIRouter(prefix="/widgets", tags=["Виджеты"])


def choice_func(choice: WidgetChoice) -> str:
    if choice == WidgetChoice.nickname:
        return "nickname"
    elif choice == WidgetChoice.weather:
        return "weather"
    elif choice == WidgetChoice.traffic:
        return "traffic"
    elif choice == WidgetChoice.date:
        return "date"
    elif choice == WidgetChoice.time:
        return "time"
    elif choice == WidgetChoice.currencies:
        return "currencies"
    elif choice == WidgetChoice.diet:
        return "diet"
    elif choice == WidgetChoice.todo:
        return "todo"
    elif choice == WidgetChoice.site_monitoring:
        return "site_monitoring"
    else:
        raise HTTPException(status_code=400, detail="Виджет не может быть добавлен")


@widgets_router.put("/change")
async def change_widgets(
    page: int = Form(..., description="Укажите номер страницы"),
    widget: WidgetChoice = Form(..., description="Виджет"),
    choice: Choice = Form(..., description="Выберите действие"),
    current_user_id: int = Depends(get_current_user)
):
    
    widget = choice_func(widget)
    choice = (choice == Choice.add)
        
    async with engine.begin() as conn:
        res = await conn.execute(text(
            f"""
            UPDATE pages
            SET {widget} = :choice
            WHERE user_id = :user_id and page = :page
            """
        ), {"user_id": current_user_id, "page": page, "choice": choice})
    
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Не удалось изменить виджет")
        
    if choice:
        return {"Виджет": "добавлен"}
    return {"Виджет": "удален"}

@widgets_router.post("/todo/creation")
async def create_todo(
    number: int             = Form(..., description="Придумайте номер задаче", ge=1),
    task: str               = Form(..., description="Опишите задачу"),
    task_date: date     = Form(..., description="Дата задачи в формате YEAR-MM-DD", examples=["2025-02-28"]),
    current_user_id: int    = Depends(get_current_user)
):
    async with engine.begin() as conn:
        res = await conn.execute(text(
            """
            INSERT INTO todos (user_id, task, number, date)
            SELECT id, :task, :number, :date FROM users
            WHERE id = :user_id
            ON CONFLICT (user_id, number) DO NOTHING
            """
        ), {"user_id": current_user_id, "task": task, "number": number, "date": task_date})

        if res.rowcount == 0:
            raise HTTPException(status_code=409, detail="Не удалось добавить задачу")
    
    return {"Задача": "добавлена"}

@widgets_router.delete("/todo/{number}")
async def delete_todo(
    number: int = Path(..., description="Номер задачи"),
    current_user_id: int = Depends(get_current_user)
):
    async with engine.begin() as conn:
        res = await conn.execute(text(
            """
            DELETE FROM todos
            WHERE user_id = :user_id AND number = :number
            """
        ), {"user_id": current_user_id, "number": number})

        if res.rowcount == 0:
            raise HTTPException(status_code=409, detail="Задачи не существует")
    
    return {"Задача": "удалена"}

@widgets_router.post("/diet/creation")
async def create_diet(
    diet_date: date         = Body(..., description="Введите дату рациона в формате YEAR-MM-DD"),
    breakfast: str | None   = Body(None, description="Завтрак"),
    lunch: str | None       = Body(None, description="Обед"),
    dinner: str | None      = Body(None, description="Ужин"),
    current_user_id: int    = Depends(get_current_user)
):
    async with engine.begin() as conn:
        res = await conn.execute(text(
            """
            INSERT INTO diets (user_id, date, breakfast, lunch, dinner)
            SELECT id, :date, :breakfast, :lunch, :dinner FROM users
            WHERE id = :user_id
            ON CONFLICT (user_id, date) DO NOTHING
            """
        ), {"user_id": current_user_id, "date": diet_date, "breakfast": breakfast, "lunch": lunch, "dinner": dinner})

        if res.rowcount == 0:
            raise HTTPException(status_code=409, detail="Не удалось добавить рацион")
    
    return {"Дневной рацион": "добавлен"}

@widgets_router.delete("/diet/{diet_date}")
async def delete_diet(
    diet_date: date         = Path(..., description="Введите дату рациона в формате YEAR-MM-DD"),
    current_user_id: int    = Depends(get_current_user)
):
    async with engine.begin() as conn:
        res = await conn.execute(text(
            """
            DELETE FROM diets
            WHERE user_id = :user_id AND date = :date
            """
        ), {"user_id": current_user_id, "date": diet_date})

        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="В этот день рациона не запланирован")
    
    return {"Рацион": "удален"}



    