from pydantic import BaseModel, Field
from typing import Optional

class AddressBase(BaseModel):
    """
    Базовая схема адреса.
    Используется для наследования в других схемах, чтобы избежать дублирования кода.
    """
    full_address: str
    street: str = Field(..., title="Улица")  # Название улицы (обязательное поле)
    house: str = Field(..., title="Дом")  # Номер дома (обязательное поле)
    entrance: Optional[int] = Field(None, title="Подъезд")  # Подъезд (необязательное поле)
    floor: Optional[int] = Field(None, title="Этаж")
    apartment: int = Field(..., title="Квартира")
    intercom: Optional[str] = None
    is_default: bool = Field(default=False, title="Основной адрес")  # Флаг, является ли адрес основным (по умолчанию False)

# Схема для создания нового адреса.
class AddressCreate(AddressBase):
    pass

class AddressRead(AddressBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class AddressUpdate(BaseModel):
    """
    Схема для обновления данных об адресе.
    Все поля необязательны, чтобы можно было обновлять только указанные данные.
    """
    entrance: Optional[int] = None
    floor: Optional[int] = None
    apartment: Optional[int] = None
    intercom: Optional[str] = None
    is_default: Optional[bool] = None



# Базовые схемы
class StoreAddressBase(BaseModel):
    full_address: Optional[str] = None
    street: str
    house: str
    floor: Optional[str] = None
    is_active: bool = True
    opening_hours: Optional[str] = None
    phone: Optional[str] = None


# Схема для создания
class StoreAddressCreate(StoreAddressBase):
    pass


# Схема для обновления (все поля опциональны)
class StoreAddressUpdate(BaseModel):
    floor: Optional[str] = None
    is_active: Optional[bool] = None
    opening_hours: Optional[str] = None
    phone: Optional[str] = None


class StoreAddressRead(StoreAddressBase):
    id: int

    class Config:
        from_attributes = True


