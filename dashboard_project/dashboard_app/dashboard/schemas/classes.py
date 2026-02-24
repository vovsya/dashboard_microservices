from enum import Enum

from pydantic import BaseModel, SecretStr, Field


class UserData(BaseModel):
    username: str = Field(min_length=4, max_length=16)
    password: SecretStr = Field(min_length=8, max_length=64)


class Token(BaseModel):
    access_token: str
    token_type: str


class WidgetChoice(str, Enum):
    nickname = "Никнейм"
    weather = "Погода"
    time = "Время"
    date = "Дата"
    traffic = "Пробки"
    currencies = "Курсы валют"
    diet = "Рацион на день"
    todo = "Список дел"
    site_monitoring = "Мониторинг сайтов"


class Choice(str, Enum):
    add = "Добавить виджет"
    delete = "Удалить виджет"
