
from datetime import datetime, timedelta, UTC
from fastapi import Request, Response, HTTPException
import jwt
from core.config import settings
from models.auth_models import User


# Создание JWT токена доступа
def create_access_token(
        data: dict,
        expires_delta: timedelta = None
) -> str:
    to_encode = data.copy()
    # Устанавливаем срок действия токена (по умолчанию 15 минут)
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})

    # Кодируем токен с использованием секретного ключа
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token() -> str:
    # Refresh token - просто случайная строка (не JWT)
    import secrets
    return secrets.token_urlsafe(64)

# Установка JWT токена в HTTP-only куку
def set_jwt_cookie(
        response: Response,
        access_token: str,
        refresh_token: str
):
    # Access token
    response.set_cookie(
        key="access_token",  # Название куки
        value=access_token,         # Значение JWT токена
        httponly=True,       # Защита от XSS-атак
        secure=True,         # Только для HTTPS (в production)
        samesite="none",      # Защита от CSRF-атак
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Время жизни в секундах
        path="/",            # Доступно для всех путей
        domain="graduate-work-backend.onrender.com",
    )

    # Refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",  # Только для эндпоинта обновления
        domain="graduate-work-backend.onrender.com",
    )


def create_tokens(user: User):
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    refresh_token = create_refresh_token()
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return access_token, refresh_token, refresh_token_expires

# Получение токена из куки запроса
def get_token_from_cookie(
        request: Request
) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return token