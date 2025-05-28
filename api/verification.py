from datetime import datetime, timedelta
from pathlib import Path
import secrets
from fastapi import Depends, HTTPException, BackgroundTasks, Response
from fastapi_mail import FastMail, MessageSchema, MessageType
from jinja2 import Template
from sqlmodel import Session, select, delete

from core.config import settings, get_mail_config
from core.database import get_session
from core.tokens import create_access_token, set_jwt_cookie
from models.auth_models import User, EmailVerificationToken, UnverifiedUser
from schemas.auth import EmailVerificationConfirm, EmailVerificationRequest


def generate_verification_token() -> str:
    """Генерация криптостойкого токена верификации"""
    return secrets.token_urlsafe(32)

async def send_verification_email(
        email: str,
        token: str,
        background_tasks: BackgroundTasks,
        username: str = None
):
    """Отправка письма с верификацией через Яндекс SMTP"""
    verification_url = f"{settings.FRONTEND_BASE_URL}/#verify-email-{token}"

    # Путь к шаблону относительно текущего файла
    template_path = Path(__file__).parent.parent / "core" / "templates" / "emails" / "email_verification.html"

    with open(template_path, "r", encoding="utf-8") as file:
        template = Template(file.read())

    html_body = template.render(
        verification_url=verification_url,
        username=username,
        site_name=settings.SITE_NAME
    )

    message = MessageSchema(
        subject="Подтверждение email адреса",
        recipients=[email],
        body=html_body,
        subtype=MessageType.html,
    )

    fm = FastMail(get_mail_config())
    background_tasks.add_task(fm.send_message, message)

def setup_verification_endpoints(app):
    @app.post("/auth/send-verification", tags=["Email Verification"])
    async def send_verification(
            request: EmailVerificationRequest,
            background_tasks: BackgroundTasks,
            session: Session = Depends(get_session)
    ):
        """Отправка письма с верификацией email"""
        user = session.exec(select(User).where(User.email == request.email)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if user.is_verified:
            return {"message": "Email уже подтвержден", "status": "success"}

        # Удаляем старые токены
        session.exec(delete(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id))

        # Создаем и сохраняем новый токен
        token = generate_verification_token()

        db_token = EmailVerificationToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        session.add(db_token)
        session.commit()

        # Отправляем письмо
        await send_verification_email(
            email=user.email,
            token=token,
            background_tasks=background_tasks,
            username=f"{user.first_name} {user.last_name}"
        )

        return {"message": "Письмо с подтверждением отправлено", "status": "success"}

    @app.post("/auth/verify-email", tags=["Email Verification"])
    async def verify_email(
            response: Response,
            confirm: EmailVerificationConfirm,
            session: Session = Depends(get_session)
    ):
        """Подтверждение email по токену"""

        # Ищем токен в таблицах
        db_token = session.exec(
            select(EmailVerificationToken)
            .where(EmailVerificationToken.token == confirm.token)
            .where(EmailVerificationToken.expires_at > datetime.utcnow())
        ).first()

        if not db_token:
            raise HTTPException(status_code=400, detail="Неверный или просроченный токен")

        # Ищем неподтвержденного пользователя
        unverified_user = session.exec(
            select(UnverifiedUser)
            .where(UnverifiedUser.verification_token == confirm.token)
        ).first()

        if not unverified_user:
            raise HTTPException(status_code=400, detail="Пользователь не найден для этого токена")

        # Создаем пользователя в основной таблице
        new_user = User.create(
            session,
            email=unverified_user.email,
            hashed_password=unverified_user.hashed_password,
            first_name=unverified_user.first_name,
            last_name=unverified_user.last_name,
            birth_date=unverified_user.birth_date,
            middle_name=unverified_user.middle_name,
            gender=unverified_user.gender,
            phone=unverified_user.phone,
            role=unverified_user.role,
            is_active=True
        )

        session.add(new_user)

        db_token.user_id = new_user.id
        session.add(db_token)

        session.delete(unverified_user)
        session.commit()

        # Генерация JWT токена для нового пользователя
        access_token = create_access_token(
            {"sub": new_user.email, "role": new_user.role},
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # Отправляем токен в ответе, без пароля
        set_jwt_cookie(response, access_token)

        return {
            "status": "success",
            "data": {
                "access_token": access_token
            }
        }

    @app.get("/auth/check-verification", tags=["Email Verification"])
    async def check_verification(
            email: str,
            session: Session = Depends(get_session)
    ):
        """Проверка статуса верификации email"""
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        return {"is_verified": user.is_verified}