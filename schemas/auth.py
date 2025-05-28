from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum
from pydantic import ConfigDict


# --- Перечисления ---
# Определяет допустимые значения для пола пользователя
class Gender(str, Enum):
    MALE = "male"  # Мужской пол
    FEMALE = "female"  # Женский пол
    UNSPECIFIED = "unspecified"  # Не указан

# Определяет роли пользователей в системе
class UserRole(str, Enum):
    USER = "user"  # Обычный пользователь
    ADMIN = "admin"  # Администратор

# --- Схемы пользователя ---
class UserBase(BaseModel):
    """Базовая схема пользователя, содержит основные данные."""
    email: str  # Email для входа
    first_name: str  # Имя пользователя
    last_name: str  # Фамилия пользователя
    birth_date: date  # Дата рождения
    middle_name: Optional[str] = None  # Отчество (необязательно)
    gender: Optional[Gender] = Gender.UNSPECIFIED  # Пол пользователя
    phone: Optional[str] = Field(None, pattern=r"^[\d\+]*$")
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = True

# Схема для регистрации нового пользователя
class UserCreate(UserBase):
    password: str  # Пароль (передается при регистрации)

# Схема для чтения данных пользователя (включает ID и даты)
class UserRead(UserBase):
    id: int  # Уникальный идентификатор пользователя
    created_at: datetime  # Дата регистрации
    last_login: Optional[datetime]  # Дата последнего входа
    model_config = ConfigDict(from_attributes=True)

# Схема для обновления данных пользователя
class UserUpdate(BaseModel):
    first_name: Optional[str]  # Новое имя пользователя
    last_name: Optional[str]  # Новая фамилия пользователя
    middle_name: Optional[str]  # Новое отчество
    birth_date: Optional[date]  # Новая дата рождения
    gender: Optional[Gender]  # Новый пол пользователя
    phone: Optional[str]  # Новый номер телефона
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None  # Изменение статуса активности


# --- Схемы для аутентификации ---
class UserLogin(BaseModel):
    email: EmailStr  # Email пользователя
    password: str  # Пароль

# --- Схемы для сессий пользователей ---
class UserSessionBase(BaseModel):
    """Базовая схема сессии пользователя."""
    user_id: int  # Идентификатор пользователя
    refresh_token: str  # Уникальный refresh-токен
    expires_at: datetime  # Дата истечения токена
    user_agent: Optional[str]  # Информация об устройстве
    ip_address: Optional[str]  # IP-адрес входа

# Схема для создания сессии
class UserSessionCreate(UserSessionBase):
    pass

# Схема для чтения данных сессии
class UserSessionRead(UserSessionBase):
    id: int  # Уникальный идентификатор сессии


class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerificationConfirm(BaseModel):
    token: str

# --- Схемы для сброса пароля ---

# используется при первом запросе на сброс пароля по email.
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetTokenConfirm(BaseModel):
    """Схема запроса для установки нового пароля по токену"""
    new_password: str

class PasswordResetTokenBase(BaseModel):
    """Базовая схема для токена сброса пароля."""
    user_id: int  # Идентификатор пользователя
    token: str  # Уникальный токен сброса пароля
    expires_at: datetime  # Дата истечения срока действия токена
    is_used: bool = False  # Был ли токен использован


# Схема для создания токена сброса пароля
class PasswordResetTokenCreate(PasswordResetTokenBase):
    pass

# Схема для чтения данных токена сброса пароля
class PasswordResetTokenRead(PasswordResetTokenBase):
    id: int  # Уникальный идентификатор токена

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


