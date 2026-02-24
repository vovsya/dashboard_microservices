from sqlalchemy.ext.asyncio import create_async_engine
import os

engine = create_async_engine(
    os.getenv("ASYNC_DB_URL"),
    echo=True
)