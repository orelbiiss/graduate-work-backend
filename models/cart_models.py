from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime, UTC, date
from enum import Enum

from models.id_mixin import IDMixin
from models.models import Drink, DrinkVolumePrice


class OrderStatus(str, Enum):
    NEW = "new"
    PROCESSING = "processing"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class DeliveryType(str, Enum):
    COURIER = "courier"
    PICKUP = "pickup"

class DeliveryTimeSlotStatus(str, Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"


class Cart(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

    items: List["CartItem"] = Relationship(
        back_populates="cart",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    cart_subtotal: int = Field(default=0)
    cart_discount: int = Field(default=0)
    cart_total: int = Field(default=0)

    session_key: Optional[str] = Field(default=None, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))



class CartItem(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cart_id: int = Field(foreign_key="cart.id")
    drink_id: int = Field(foreign_key="drink.id")
    drink_volume_price_id: int = Field(foreign_key="drinkvolumeprice.id")
    quantity: int = Field(default=1, ge=1)

    # Связи
    drink: Drink = Relationship()
    drink_volume_price: DrinkVolumePrice = Relationship()
    cart: "Cart" = Relationship(back_populates="items")

    # Расчеты для позиции
    item_subtotal: int = Field(default=0)
    item_discount: int = Field(default=0)
    item_total: int = Field(default=0)

    # Базовые свойства товара
    @property
    def name(self) -> str:
        return self.drink_volume_price.drink.name

    @property
    def img_src(self) -> Optional[str]:
        return self.drink_volume_price.img_src or self.drink_volume_price.drink.img_src

    @property
    def volume(self) -> Optional[int]:
        return self.drink_volume_price.volume

    @property
    def ingredients(self) -> str:
        return self.drink_volume_price.drink.ingredients

    # Ценовые свойства
    @property
    def price_original(self) -> int:
        """Цена без скидки за 1 единицу"""
        return self.drink_volume_price.price

    @property
    def sale(self) -> Optional[int]:
        """Процент скидки (из объема или глобальный)"""
        return self.drink_volume_price.sale or self.drink_volume_price.drink.global_sale

    @property
    def price_final(self) -> int:
        """Цена со скидкой за 1 единицу"""
        discount = self.sale or 0
        return round(self.price_original * (100 - discount) / 100)


class DeliveryInfo(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", nullable=False)

    # Информация о доставке
    full_address: str = Field(nullable=True, max_length=500)
    delivery_comment: Optional[str] = Field(nullable=True, max_length=500)
    delivery_date: Optional[date] = Field(nullable=True)
    delivery_time: Optional[str] = Field(nullable=True)
    time_slot_id: Optional[int] = Field(foreign_key="deliverytimeslot.id", nullable=True)
    customer_name: Optional[str] = Field(nullable=True)
    customer_phone: Optional[str] = Field(nullable=True)

    delivery_price: Optional[int] = Field(default=0, nullable=False)

    # Связь с заказом
    order: "Order" = Relationship( back_populates="delivery_info", sa_relationship_kwargs={
                                                                                "cascade": "all, delete",
                                                                                "passive_deletes": True
                                                                            })
    time_slot: Optional["DeliveryTimeSlot"] = Relationship(back_populates="delivery_info")


class Order(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=True)

    # Финансовые данные
    order_subtotal: int = Field(default=0)
    order_discount: int = Field(default=0)
    order_total: int = Field(default=0)

    # Системная информация
    address_id: Optional[int] = Field(default=None, foreign_key="address.id", nullable=True)
    store_address_id: Optional[int] = Field(default=None, foreign_key="storeaddress.id", nullable=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: OrderStatus = Field(default=OrderStatus.NEW)
    delivery_type: DeliveryType = Field(default=DeliveryType.PICKUP)

    # Связи
    user: Optional["User"] = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(back_populates="order")
    address: Optional["Address"] = Relationship(back_populates="orders")
    store_address: Optional["StoreAddress"] = Relationship(
        back_populates="orders",
        sa_relationship_kwargs={"passive_deletes": True}
    )
    delivery_info: Optional["DeliveryInfo"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={
            "cascade": "all, delete",
            "passive_deletes": True
        }
    )


class OrderItem(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    drink_id: int = Field(foreign_key="drink.id")
    drink_volume_price_id: int = Field(foreign_key="drinkvolumeprice.id")
    quantity: int = Field(ge=1)

    # Фиксированные данные на момент заказа
    price_original: int  # Цена без скидки
    price_final: int
    sale: Optional[int] = None  # Процент скидки
    item_subtotal: int
    item_discount: int
    item_total: int
    volume: Optional[int] = None  # Объем

    # Связи
    drink: Drink = Relationship()
    drink_volume_price: DrinkVolumePrice = Relationship(back_populates="order_items")
    order: Order = Relationship(back_populates="items")

    # Вычисляемые свойства
    @property
    def name(self) -> str:
        return self.drink_volume_price.drink.name if self.drink_volume_price else "Неизвестно"


class DeliveryTimeSlot(SQLModel, IDMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: date
    time_slot: str
    max_orders: int = Field(default=5)
    current_orders: int = Field(default=0)
    status: DeliveryTimeSlotStatus = Field(default=DeliveryTimeSlotStatus.AVAILABLE)

    delivery_info: List["DeliveryInfo"] = Relationship(back_populates="time_slot")