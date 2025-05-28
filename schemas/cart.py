from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, date
from enum import Enum
from schemas.address import AddressRead, StoreAddressRead


# Enum статусов заказа
class OrderStatus(str, Enum):
    NEW = "new"
    PROCESSING = "processing"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Enum типов доставки
class DeliveryType(str, Enum):
    COURIER = "courier"
    PICKUP = "pickup"

class DeliveryTimeSlotStatus(str, Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"


# Базовые схемы для корзины
class CartItemBase(BaseModel):
    """Базовая схема элемента корзины"""
    drink_volume_price_id: int  # ID варианта напитка (объем+цена)
    quantity: int = 1  # Количество по умолчанию 1


class CartItemCreate(CartItemBase):
    """Схема для создания элемента корзины"""
    pass


class CartItemRead(CartItemBase):
    """Схема для чтения элемента корзины"""
    id: int  # ID элемента корзины
    cart_id: int  # ID корзины
    drink_id: int  # ID напитка
    name: str  # Название напитка
    img_src: Optional[str] = None  # URL изображения
    volume: int  # Объем в мл
    price_original: int  # Цена без скидки
    sale: Optional[int] = None  # Процент скидки
    price_final: int  # Цена со скидкой
    ingredients: str  # Состав напитка

    # Расчетные поля
    item_subtotal: int  # Сумма без скидки (price * quantity)
    item_discount: int  # Сумма скидки по позиции
    item_total: int  # Итоговая сумма (price_final * quantity)

    model_config = ConfigDict(from_attributes=True)


class CartRead(BaseModel):
    """Схема для чтения корзины"""
    id: int  # ID корзины
    user_id: Optional[int]  # ID пользователя
    items: List[CartItemRead] = []  # Список товаров
    cart_quantity: int

    # Расчетные поля для всей корзины
    cart_subtotal: int  # Общая сумма без скидок
    cart_discount: int  # Общая сумма скидок
    cart_total: int  # Итоговая сумма к оплате

    model_config = ConfigDict(from_attributes=True)


# Схемы для заказов
class OrderItemBase(BaseModel):
    """Базовая схема элемента заказа"""
    drink_id: int  # ID напитка
    drink_volume_price_id: int  # ID варианта напитка
    quantity: int = Field(..., gt=0)  # Количество (>0)
    price_original: int
    price_final: int
    sale: Optional[int] = None  # Скидка на момент заказа
    volume: Optional[int] = None  # Объем
    item_subtotal: int
    item_discount: int
    item_total: int


class OrderItemCreate(OrderItemBase):
    """Схема для создания элемента заказа"""
    pass


class OrderItemRead(OrderItemBase):
    """Схема для чтения элемента заказа"""
    id: int  # ID элемента заказа
    order_id: int  # ID заказа
    name: str  # Название напитка
    img_src: Optional[str] = None  # URL изображения

    model_config = ConfigDict(from_attributes=True)

# Схема данных о доставке
class DeliveryInfoBase(BaseModel):
    full_address: Optional[str] = Field(None, max_length=500)
    delivery_comment: Optional[str] = Field(None, max_length=500)
    delivery_date: Optional[date] = None
    delivery_time: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    delivery_price: int

class DeliveryInfoCreate(DeliveryInfoBase):
    pass

class DeliveryInfoRead(DeliveryInfoBase):
    id: int
    order_id: int
    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    address_id: Optional[int] = None
    store_address_id: Optional[int] = None
    status: OrderStatus = OrderStatus.NEW
    delivery_type: DeliveryType
    order_subtotal: int
    order_discount: int
    order_total: int


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]
    delivery_info: Optional[DeliveryInfoCreate] = None
    customer_name: str
    customer_phone: str

class DeliveryTimeSlotBase(BaseModel):
    date: date
    time_slot: str
    max_orders: int = Field(default=5, gt=0)
    current_orders: int = Field(default=0, ge=0)
    status: DeliveryTimeSlotStatus = Field(default=DeliveryTimeSlotStatus.AVAILABLE)

class DeliveryTimeSlotCreate(DeliveryTimeSlotBase):
    pass

class DeliveryTimeSlotRead(DeliveryTimeSlotBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    order_subtotal: int
    order_discount: int
    order_total: int
    address_id: Optional[int] = None
    store_address_id: Optional[int] = None
    created_at: datetime
    status: OrderStatus
    delivery_type: DeliveryType
    items: List[OrderItemRead]
    address: Optional[AddressRead] = None
    store_address: Optional[StoreAddressRead] = None
    delivery_info: Optional[DeliveryInfoRead] = None

    class Config:
        from_attributes = True


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    delivery_comment: Optional[str] = None
    delivery_time: Optional[str] = None
    time_slot_id: Optional[int] = None
    model_config = ConfigDict(extra="forbid")

class OrderCreateResponse(BaseModel):
    """Упрощённая схема для ответа после создания заказа"""
    id: int
    order_total: int
    status: OrderStatus
    delivery_type: DeliveryType
    created_at: datetime


    class Config:
        from_attributes = True

class OrderCreateRequest(BaseModel):
    delivery_type: DeliveryType
    delivery_price: int = Field(..., ge=0)
    delivery_date: Optional[date] = None
    time_slot_id: Optional[int] = None
    store_address_id: Optional[int] = None
    delivery_comment: Optional[str] = None
