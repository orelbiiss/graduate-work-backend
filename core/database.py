import os

from sqlmodel import create_engine, SQLModel, Session
from pathlib import Path

from core.config import settings

DB_SSL_CA_PATH = str(
    Path(os.getenv('DB_SSL_CA_PATH'))
    if Path(os.getenv('DB_SSL_CA_PATH')).exists()
    else os.getenv('RENDER_SSL_PATH')
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "ssl_ca": settings.DB_SSL_CA_PATH  # путь к ssl сертификату
    },
    echo=True
)

def get_session():
    with Session(engine) as session:
        yield session

def create_tables():
    """Создание таблиц при старте приложения"""
    SQLModel.metadata.create_all(engine)