# Стандартные библиотеки
import uuid
from pathlib import Path
from datetime import datetime, timedelta

# Внешние библиотеки
from fastapi import HTTPException, Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from fastapi_mail import FastMail, MessageSchema, MessageType
from jinja2 import Template
from passlib.context import CryptContext
from sqlmodel import Session

# Местные импорты
from core.config import get_mail_config, settings
from core.database import get_session
from core.dependencies import get_current_user
from models.auth_models import User, PasswordResetToken
from schemas.auth import PasswordChangeRequest, PasswordResetRequest, PasswordResetTokenConfirm

###################
# ПРОВЕРКА ДОСТУПА
###################

# Инициализация инструментов безопасности
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # Для хеширования паролей
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/signin", auto_error=False)  # Для совместимости

# Хеширование пароля с использованием bcrypt
def hash_password(
        password: str
) -> str:
    return pwd_context.hash(password)

# Сравнение пароля с его хешем
def verify_password(
        plain_password: str,
        hashed_password: str
) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_unique_token():
    """Генерация уникального токена для сброса пароля"""
    return str(uuid.uuid4())


async def send_reset_email(
        email: str,
        token: str,
        background_tasks: BackgroundTasks
):
    """Функция для отправки письма через Яндекс SMTP"""

    reset_url = f"{settings.FRONTEND_BASE_URL}/#password-reset-confirm-{token}"

    template_path = Path(__file__).parent.parent / "core" / "templates" / "emails" / "reset_password.html"
    with open(template_path, "r", encoding="utf-8") as file:
        template_content = file.read()

    template = Template(template_content)
    html_body = template.render(reset_url=reset_url)

    # Используем Яндекс SMTP конфигурацию
    mail_config = get_mail_config()
    fm = FastMail(mail_config)

    message = MessageSchema(
        subject="Запрос на сброс пароля",
        recipients=[email],
        body=html_body,
        subtype=MessageType.html,
    )

    background_tasks.add_task(fm.send_message, message)

def setup_password_endpoints(app):

    @app.post("/user/change-password", tags=["Password"])
    def change_password(
            data: PasswordChangeRequest,
            current_user: User = Depends(get_current_user),
            session: Session = Depends(get_session)
    ):
        """Обновление пароля авторизованного пользователя"""

        # Проверка, что старый пароль совпадает с хэшированным паролем
        if not verify_password(data.old_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Неверный старый пароль")

        # Проверка, что новый пароль отличается от старого
        if data.old_password == data.new_password:
            raise HTTPException(status_code=400, detail="Новый пароль не должен совпадать с старым")

        # Обновление пароля
        current_user.hashed_password = hash_password(data.new_password)
        session.add(current_user)
        session.commit()

        return {"message": "Пароль успешно изменён"}

    @app.post("/password-reset/initiate", tags=["Password Reset"])
    async def handle_password_reset_request(
            background_tasks: BackgroundTasks,
            data: PasswordResetRequest,
            session: Session = Depends(get_session)
    ):
        """
        Универсальный обработчик запросов сброса пароля:
        - Создает новый токен, если нет активных
        - Обновляет существующий токен, если он еще активен
        """
        # Ищем пользователя по email
        user = session.query(User).filter(User.email == data.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Проверяем существование активного токена
        existing_token = session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        ).first()

        if existing_token:
            # Обновляем существующий токен
            existing_token.token = generate_unique_token()
            existing_token.expires_at = datetime.utcnow() + timedelta(minutes=15)
            token = existing_token.token
            message = "Токен сброса пароля повторно отправлен на почту."
        else:
            # Создаем новый токен
            token = generate_unique_token()
            session.add(PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                is_used=False
            ))
            message = "Письмо для сброса пароля отправлено на почту."

        session.commit()

        # Отправляем письмо с токеном
        await send_reset_email(user.email, token, background_tasks)
        return {"message": message}

    # Подтверждение сброса пароля по токену
    @app.post("/password-reset/confirm/{token}", tags=["Password Reset"])
    def confirm_password_reset(
            token: str,  # Из URL
            data: PasswordResetTokenConfirm,  # Только new_password
            session: Session = Depends(get_session)
    ):
        # Логирование для отладки
        print(f"Получен токен из URL: {token}")

        # Ищем токен (с очисткой пробелов)
        token_entry = session.query(PasswordResetToken).filter(
            PasswordResetToken.token == token.strip()
        ).first()

        # Проверяем валидность и срок действия токена
        if not token_entry:
            raise HTTPException(
                status_code=400,
                detail= "invalid_link"
            )

        if token_entry.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail= "expired_link"
            )

        if token_entry.is_used:
            raise HTTPException(
                status_code=400,
                detail="already_used"
            )

        # Обновляем пароль пользователя
        user = session.get(User, token_entry.user_id)
        user.hashed_password = hash_password(data.new_password)
        session.add(user)

        # Помечаем токен как использованный
        token_entry.is_used = True
        session.add(token_entry)

        session.commit()

        return {"message": "Пароль успешно сброшен"}
