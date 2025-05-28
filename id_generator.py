from datetime import datetime
import random
from sqlmodel import Session, select
from typing import Type, Any


def generate_unique_id(session: Session, model: Type[Any], max_attempts: int = 5) -> int:
    """
    Генерация 8-значного уникального ID (10,000,000 - 99,999,999)
    """
    for _ in range(max_attempts):
        # 1. Берем 7 цифр из текущего timestamp (мс)
        timestamp_part = int(datetime.now().timestamp() * 1000) % 10_000_000

        # 2. Добавляем 1 случайную цифру в начало (чтобы гарантировать 8 цифр)
        random_prefix = random.randint(1, 9)  # от 1 до 9 (исключаем ведущий ноль)

        # 3. Формируем 8-значный ID
        unique_id = random_prefix * 10_000_000 + timestamp_part

        # 4. Проверяем уникальность (сохраняем оригинальный стиль проверки)
        result = session.execute(select(model).where(model.id == unique_id)).scalar()
        if not result:
            return unique_id

    raise ValueError("Не удалось сгенерировать уникальный ID")


def create_with_unique_id(session: Session, model: Type[Any], **kwargs) -> Any:
    """
    Создание объекта с уникальным ID
    """
    unique_id = generate_unique_id(session, model)
    obj = model(id=unique_id, **kwargs)
    session.add(obj)
    session.flush()
    return obj