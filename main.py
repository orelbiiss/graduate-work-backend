from fastapi import FastAPI

from api.admin import setup_admin_endpoints
from api.catalog import setup_catalog_endpoints
from api.cart import setup_cart_endpoints
from api.address import setup_address_endpoints
from api.auth import setup_auth_endpoints
from api.order import setup_order_endpoints
from api.password import setup_password_endpoints
from api.verification import setup_verification_endpoints
from core.database import create_tables
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Для фронтенда на localhost
        "http://127.0.0.1:3000",  # Альтернативный адрес фронтенда
    ],  # Укажите домен вашего фронтенда
    allow_credentials=True,  # Разрешить куки и авторизацию
    allow_methods=["*"],  # Разрешить все HTTP-методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Инициализация БД
create_tables()

# Подключение эндпоинтов
setup_catalog_endpoints(app)
setup_auth_endpoints(app)
setup_cart_endpoints(app)
setup_order_endpoints(app)
setup_admin_endpoints(app)
setup_address_endpoints(app)
setup_password_endpoints(app)
setup_verification_endpoints(app)
