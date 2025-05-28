
from datetime import datetime, timedelta, UTC
from fastapi import Request, Response, HTTPException
import jwt
from core.config import settings

# Создание JWT токена доступа
def create_access_token(
        data: dict,
        expires_delta: timedelta = None
) -> str:
    to_encode = data.copy()
    # Устанавливаем срок действия токена (по умолчанию 15 минут)
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})

    # Кодируем токен с использованием секретного ключа
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# Установка JWT токена в HTTP-only куку
def set_jwt_cookie(
        response: Response,
        token: str
):
    response.set_cookie(
        key="access_token",  # Название куки
        value=token,         # Значение JWT токена
        httponly=True,       # Защита от XSS-атак
        secure=False,         # Только для HTTPS (в production)
        samesite="lax",      # Защита от CSRF-атак
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Время жизни в секундах
        path="/",            # Доступно для всех путей
        domain=None,
    )

# Получение токена из куки запроса
def get_token_from_cookie(
        request: Request
) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return token