import os

from sqlmodel import create_engine, SQLModel, Session
from pathlib import Path

from core.config import settings

# 1. Получаем пути из переменных окружения
LOCAL_SSL_PATH = os.getenv('DB_SSL_CA_PATH')  # Локальный путь из .env
RENDER_SSL_PATH = os.getenv('RENDER_SSL_PATH')  # Путь на Render

# 2. Безопасный выбор пути
DB_SSL_CA_PATH = None

if LOCAL_SSL_PATH and Path(LOCAL_SSL_PATH).exists():
    DB_SSL_CA_PATH = LOCAL_SSL_PATH
elif RENDER_SSL_PATH:
    DB_SSL_CA_PATH = RENDER_SSL_PATH

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