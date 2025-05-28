from pydantic_settings import BaseSettings
from pathlib import Path

from fastapi_mail import ConnectionConfig


class Settings(BaseSettings):
    # Указываем путь к базе данных, которая будет храниться в папке проекта
    DATABASE_URL: str = "mysql+mysqlconnector://root:root@localhost/zerop_db" # База данных будет храниться в файле drink_shop_db.db
    ALGORITHM: str = "HS256"  # Алгоритм шифрования JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # Время жизни токена (мин)
    SECRET_KEY: str
    CLIENT_ID: str
    CLIENT_SECRET: str
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24

    # Настройки Yandex Object Storage
    YC_ACCESS_KEY_ID: str
    YC_SECRET_ACCESS_KEY: str
    YC_BUCKET_NAME: str
    YC_ENDPOINT_URL: str

    # Настройки Yandex Translate API
    YC_TRANSLATE_API_KEY: str
    YC_FOLDER_ID: str
    YC_TRANSLATE_API_URL: str = "https://translate.api.cloud.yandex.net/translate/v2/translate"

    # Настройки Яндекс SMTP
    YANDEX_EMAIL: str
    YANDEX_APP_PASSWORD: str  # Пароль приложения из Яндекс ID
    MAIL_FROM_NAME: str = "ZeroPercent: ваш партнер в заботе о вас и вашем здоровье"  # Имя отправителя
    SITE_NAME: str = "ZeroPercent"

    FRONTEND_BASE_URL: str = "http://localhost:3000"



    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        env_file_encoding = 'utf-8'


settings = Settings()

def get_mail_config():
    """Конфигурация для Яндекс SMTP"""
    return ConnectionConfig(
        MAIL_USERNAME=settings.YANDEX_EMAIL,
        MAIL_PASSWORD=settings.YANDEX_APP_PASSWORD,
        MAIL_FROM=settings.YANDEX_EMAIL,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=465,  # Стандартный порт для Яндекс SMTP с SSL
        MAIL_SERVER="smtp.yandex.ru",
        MAIL_STARTTLS=False,  # Для Яндекс не используется
        MAIL_SSL_TLS=True,  # Обязательно для Яндекс
        USE_CREDENTIALS=True,
        TEMPLATE_FOLDER=Path(__file__).parent / "templates"
    )