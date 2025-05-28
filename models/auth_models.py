from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime, date, timedelta, UTC
from enum import Enum

from models.id_mixin import IDMixin


# ─────────────────────── Перечисления ───────────────────────

class Gender(str, Enum):
    """Пол пользователя (мужской/женский/не указан)"""
    MALE = "male"       # Мужской пол
    FEMALE = "female"   # Женский пол
    UNSPECIFIED = "unspecified"  # Пользователь не указал пол

class UserRole(str, Enum):
    """Роли пользователей в системе"""
    USER = "user"    # Обычный пользователь (базовые права)
    ADMIN = "admin"  # Администратор (полные права доступа)


# ─────────────────────── Адрес пользователя ───────────────────────

class Address(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)  # ID адреса
    user_id: int = Field(foreign_key="user.id")  # Ссылка на пользователя
    # Основные обязательные поля
    full_address: str = Field(nullable=False, max_length=500)
    street: str = Field(nullable=False, max_length=255)   # Улица
    house: str = Field(nullable=False, max_length=50)  # Дом

    # Детали доставки
    entrance: Optional[int] = None  # Подъезд (необязательно)
    intercom: Optional[str] = Field(default=None, max_length=50)
    floor: Optional[int] = None  # Этаж (необязательно)
    apartment: Optional[int] = None  # Квартира (обязательно)

    # Служебные поля
    is_default: bool = Field(default=False)  # Флаг основного адреса
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    user: "User" = Relationship(back_populates="addresses")
    orders: List["Order"] = Relationship(back_populates="address",
                                         sa_relationship_kwargs={"passive_deletes": True})

# ─────────────────────── Адрес магазина ───────────────────────

class StoreAddress(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_address: str = Field(nullable=False, max_length=500)
    street: str
    house: str
    floor: Optional[str] = None
    opening_hours: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    orders: List["Order"] = Relationship(back_populates="store_address",
                                         sa_relationship_kwargs={"passive_deletes": True})

# ─────────────────────── Пользователь ───────────────────────

class UnverifiedUser(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = Field(default=UserRole.USER)
    verification_token: str
    token_expires: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class User(SQLModel, IDMixin, table=True):

    # --- Идентификация ---
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)

    # --- Персональные данные ---
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    middle_name: Optional[str] = None
    birth_date: date
    gender: Optional[Gender] = None
    phone: Optional[str] = None

    # --- Системные настройки ---
    role: UserRole = Field(default=UserRole.USER)  # Роль (по умолчанию - обычный пользователь)
    is_active: bool = Field(default=True)  # Активен ли аккаунт (может быть заблокирован)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))  # Дата регистрации
    last_login: Optional[datetime] = None  # Дата последнего входа

    # --- Связи с другими таблицами ---
    sessions: List["UserSession"] = Relationship(back_populates="user",
                                                 sa_relationship_kwargs={"cascade": "all, delete-orphan"})  # Активные сессии
    password_reset_tokens: List["PasswordResetToken"] = Relationship(back_populates="user",
                                                                     sa_relationship_kwargs={"cascade": "all, delete-orphan"})  # Токены сброса пароля
    addresses: List[Address] = Relationship(back_populates="user",
                                            sa_relationship_kwargs={"cascade": "all, delete-orphan"})  # Связь с адресами пользователя
    cart: List["Cart"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    orders: List["Order"] = Relationship(back_populates="user",
                                         sa_relationship_kwargs={"passive_deletes": True })

# ─────────────────────── Сессия пользователя ───────────────────────

class UserSession(SQLModel, IDMixin, table=True):
    """Модель для хранения активных сессий пользователя"""
    id: Optional[int] = Field(default=None, primary_key=True)  # ID сессии
    user_id: int = Field(foreign_key="user.id")  # Ссылка на пользователя

    # --- Данные сессии ---
    refresh_token: str = Field(unique=True, index=True)  # Уникальный refresh-токен
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC) + timedelta(days=30))  # Срок действия (30 дней)

    # --- Информация об устройстве ---
    user_agent: Optional[str] = None  # Информация о браузере/устройстве
    ip_address: Optional[str] = None  # IP-адрес входа

    user: User = Relationship(back_populates="sessions")  # Обратная связь с пользователем

# ─────────────────────── Токен верификации Email ───────────────────────

class EmailVerificationToken(SQLModel, IDMixin, table=True):
    """Токены для верификации email"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    token: str = Field(unique=True, index=True)
    expires_at: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(hours=24))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    user: User = Relationship()

# ─────────────────────── Токен сброса пароля ───────────────────────

class PasswordResetToken(SQLModel, table=True):
    """Токены для сброса пароля"""
    id: Optional[int] = Field(default=None, primary_key=True)  # ID токена
    user_id: int = Field(foreign_key="user.id")  # Ссылка на пользователя

    # --- Данные токена ---
    token: str = Field(unique=True, index=True)  # Уникальный токен сброса
    expires_at: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(hours=1))
    is_used: bool = Field(default=False)  # Был ли токен использован

    user: User = Relationship(back_populates="password_reset_tokens")  # Обратная связь

