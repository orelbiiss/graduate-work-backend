from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from models.id_mixin import IDMixin


# Модель для напитка (основная модель)
class DrinkBase(SQLModel):
    name: str
    img_src: Optional[str] = None
    ingredients: str
    product_description: str
    global_sale: Optional[int] = None

# Модель для цен и объемов напитков
class DrinkVolumePrice(SQLModel, IDMixin, table=True):
    id: int = Field(default=None, primary_key=True)
    volume: int
    price: int
    quantity: int
    sale: Optional[int] = None
    img_src: Optional[str] = None
    drink_id: int = Field(foreign_key="drink.id")  # Ссылка на напиток
    drink: "Drink" = Relationship(back_populates="volume_prices")
    order_items: List["OrderItem"] = Relationship(back_populates="drink_volume_price",
                                                  sa_relationship_kwargs={"passive_deletes": True})


# Основная модель напитка для базы данных
class Drink(DrinkBase, IDMixin, table=True):
    id: int = Field(default=None, primary_key=True)
    section_id: str = Field(foreign_key="section.id", nullable=False)  # Связь с разделом
    section: "Section" = Relationship(back_populates="drinks")
    volume_prices: List[DrinkVolumePrice] = Relationship(back_populates="drink",
                                                         sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# Модель для секции
class SectionBase(SQLModel):
    title: str
    img_src: Optional[str] = None

# Основная модель секции
class Section(SectionBase, table=True):
    id: str = Field(primary_key=True)
    drinks: List[Drink] = Relationship(back_populates="section",
                                       sa_relationship_kwargs={"cascade": "all, delete-orphan"})

