from dashboard_app.dashboard.schemas.classes import UserData, Token
from dashboard_app.dashboard.db.db_engine import engine
from fastapi import Depends, HTTPException, Form, APIRouter
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import asyncio
from dashboard_app.dashboard.security.auth import pwd_context, verify_password, create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm


profile_router = APIRouter(prefix="/profile", tags=["Профиль"])

@profile_router.post("/register")
async def create_user(userinfo: UserData):
    hashed_pass = await asyncio.to_thread(
        pwd_context.hash,
        userinfo.password.get_secret_value()
    )

    try:  
        async with engine.begin() as connection:
            await connection.execute(text(
                """
                INSERT INTO users (username, secretpass) VALUES (:username, :secretpass)
                """
            ), {"username": userinfo.username, "secretpass": hashed_pass})

    except IntegrityError:
        raise HTTPException(status_code=409, detail="Пользователь с таким именем уже существует")
    
    return {"Вы зарегистрировались": "Теперь Вы можете авторизоваться"}

@profile_router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    async with engine.begin() as connection:
        user_data = await connection.execute(text(
            "SELECT id, secretpass FROM users WHERE username = :name"
        ), {"name": form_data.username})

        user_data = user_data.mappings().first()
       
    if not user_data or not await asyncio.to_thread(verify_password, form_data.password, user_data["secretpass"]):
        raise HTTPException(
            status_code=401,
            detail="Неправильное имя пользователя или пароль",
        )

    access_token = await asyncio.to_thread(create_access_token, {"sub": str(user_data["id"])})
    return {"access_token": access_token, "token_type": "bearer"}

@profile_router.get("/info")
async def get_profile_info(current_user_id: int = Depends(get_current_user)):
    async with engine.begin() as connection:
        data = await connection.execute(text(
            """
            SELECT u.id, u.username, p.page FROM users u
            LEFT JOIN pages p ON p.user_id = u.id
            WHERE u.id = :id
            ORDER BY p.page
            """
        ), {"id": current_user_id})
        
        data = data.mappings().all()

        if not data:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        data = {
            "id": data[0]["id"],
            "username": data[0]["username"],
            "pages": [row["page"] for row in data if row["page"] is not None]}
    
    return {"данные пользователя": data}

@profile_router.patch("/changename")
async def change_name(
    password: str = Form(..., description="Введите пароль", json_schema_extra={"format": "password"}),
    new_username: str = Form(..., description="Новое имя:"),
    current_user_id: int = Depends(get_current_user)
):
    async with engine.begin() as connection:

        db_password = await connection.execute(text(
            """
            SELECT secretpass FROM users
            WHERE id = :id
            """
        ), {"id": current_user_id})
        
        db_password = db_password.scalar_one_or_none()

        if db_password is None or not await asyncio.to_thread(verify_password, password, db_password):
            raise HTTPException(status_code=403, detail="Пользователь не существует или неверный паролль")

        try:
            await connection.execute(text(
                """
                UPDATE users
                SET username = :new_username
                WHERE id = :id
                """
            ), {"new_username": new_username, "id": current_user_id})

        except IntegrityError:
            raise HTTPException(status_code=409, detail="Имя занято")
    
    return {"Имя пользователя изменено": "Перелогиньтесь для доступа к кошельку]"}

@profile_router.delete("/delete")
async def delete_profile(
    password1: str = Form(..., description="Введите пароль", json_schema_extra={"format": "password"}),
    password2: str = Form(..., description="Повторите пароль", json_schema_extra={"format": "password"}),
    confirm: str = Form(..., description="Введите 'ПОДТВЕРДИТЬ'"),
    current_user_id: int = Depends(get_current_user)
    ):

    if confirm != "ПОДТВЕРДИТЬ":
        raise HTTPException(status_code=401, detail="Требуется подтверждение")
    
    if password1 != password2:
        raise HTTPException(status_code=401, detail="Пароли не совпадают")
    
    async with engine.begin() as connection:
        db_password = (await connection.execute(text(
            """
            SELECT secretpass FROM users
            WHERE id = :id
            """
        ), {"id": current_user_id})).scalar_one_or_none()

        if not db_password or not await asyncio.to_thread(verify_password, password1, db_password):
            raise HTTPException(status_code=401, detail="Неверный пароль")
    
        await connection.execute(text(
            """
            DELETE FROM pages
            WHERE user_id = :user_id;
            """
        ), {"user_id": current_user_id})

        await connection.execute(text(
            """
            DELETE FROM todos
            WHERE user_id = :user_id
            """
        ), {"user_id": current_user_id})

        await connection.execute(text(
            """
            DELETE FROM diets
            WHERE user_id = :user_id
            """
        ), {"user_id": current_user_id})

        await connection.execute(text(
            """
            DELETE FROM users
            WHERE id = :id;
            """
        ), {"id": current_user_id})

    return {"Аккаунт": "Удален"}

