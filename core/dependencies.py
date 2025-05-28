from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
import jwt
from core.config import settings
from core.database import get_session
from sqlmodel import Session, select

from core.tokens import get_token_from_cookie, create_access_token, set_jwt_cookie
from models.auth_models import User
from datetime import datetime, timedelta

# Проверка токена и возврат текущего пользователя (работает через куки)
def get_current_user(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
) -> User:
    try:
        # Получаем токен из куки
        token = get_token_from_cookie(request)

        # Декодируем токен с использованием секретного ключа
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # Извлекаем email из токена
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Неверный токен")

        exp = datetime.utcfromtimestamp(payload["exp"])
        remaining = exp - datetime.utcnow()

        # Если осталось менее суток — обновляем токен
        if remaining < timedelta(days=1):
            user = session.exec(select(User).where(User.email == email)).first()
            if user:
                new_token = create_access_token(
                    {"sub": user.email, "role": user.role},
                    timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                )
                set_jwt_cookie(response, new_token)

        # Ищем пользователя в базе данных по email из токена
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return user

    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Ошибка токена: {str(e)}")

async def get_user_or_none(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
) -> Optional[User]:
    """Возвращает пользователя или None если не авторизован"""
    try:
        return get_current_user(request, response, session)
    except HTTPException:
        return None

# Функция для получения роли текущего пользователя
def get_role_from_token(
        request: Request
) -> str:
    try:
        token = get_token_from_cookie(request)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        role = payload.get("role")  # Извлекаем роль из токена

        if role is None:
            raise HTTPException(status_code=401, detail="Роль не найдена")
        return role
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Ошибка токена")