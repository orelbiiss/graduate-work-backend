from sqlmodel import create_engine, SQLModel, Session
from pathlib import Path

# Путь к БД в корне проекта
BASE_DIR = Path(__file__).parent.parent
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost/zerop_db"

engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

def create_tables():
    """Создание таблиц при старте приложения"""
    SQLModel.metadata.create_all(engine)