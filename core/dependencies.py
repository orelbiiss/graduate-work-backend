from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
import jwt
from core.config import settings
from core.database import get_session
from sqlmodel import Session, select

from core.tokens import get_token_from_cookie, set_jwt_cookie, create_tokens
from models.auth_models import User, UserSession
from datetime import datetime, timedelta, UTC

# Проверка токена и возврат текущего пользователя (работает через куки)
def get_current_user(
        request: Request,
        response: Response,
        session: Session = Depends(get_session)
) -> User:
    try:
        # 1. Получение access token
        access_token = request.cookies.get("access_token")

        # 2. Проверка access token
        if access_token:
            try:
                payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                email = payload.get("sub")

                if email:
                    user = session.exec(select(User).where(User.email == email)).first()
                    if user and user.is_active:
                        # 3. Проверка refresh token
                        refresh_token = request.cookies.get("refresh_token")
                        if refresh_token:
                            user_session = session.exec(
                                select(UserSession)
                                .where(UserSession.refresh_token == refresh_token)
                                .where(UserSession.user_id == user.id)
                            ).first()

                            # Явно приводим даты к UTC перед сравнением
                            if user_session and user_session.expires_at.replace(tzinfo=UTC) > datetime.now(UTC):
                                user_session.expires_at = datetime.now(UTC) + timedelta(
                                    days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
                                session.add(user_session)
                                session.commit()
                                return user

                        raise HTTPException(status_code=401, detail="Требуется авторизация")

            except jwt.ExpiredSignatureError:
                pass
            except jwt.PyJWTError:
                raise HTTPException(status_code=401, detail="Неверный токен")

        # 4. Пробуем refresh token
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Требуется авторизация")

        # 5. Проверка refresh token в базе
        user_session = session.exec(
            select(UserSession)
            .where(UserSession.refresh_token == refresh_token)
            .where(UserSession.expires_at.replace(tzinfo=UTC) > datetime.now(UTC))
        ).first()

        if not user_session:
            raise HTTPException(status_code=401, detail="Сессия истекла")

        # 6. Получение пользователя
        user = session.get(User, user_session.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        # 7. Генерация новых токенов
        new_access_token, new_refresh_token, _ = create_tokens(user)

        # 8. Обновление сессии
        user_session.refresh_token = new_refresh_token
        user_session.expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session.add(user_session)
        session.commit()

        # 9. Установление куки
        set_jwt_cookie(response, new_access_token, new_refresh_token)

        return user

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

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