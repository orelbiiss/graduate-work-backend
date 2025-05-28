from pydantic import BaseModel
from typing import List, Optional

# Схема для создания объема и цены напитка
class DrinkVolumePriceCreate(BaseModel):
    id: Optional[int] = None
    img_src: Optional[str] = None
    volume: int
    price: int
    quantity: int  # Количество на складе
    sale: Optional[int] = None

class DrinkVolumePriceRead(BaseModel):
    id: int
    img_src: Optional[str] = None
    volume: float
    price: float
    quantity: int
    sale: Optional[float] = None

    class Config:
        orm_mode = True

class DrinkVolumePriceUpdate(BaseModel):
    volume: Optional[int] = None
    price: Optional[int] = None
    quantity: Optional[int] = None
    sale: Optional[int] = None
    img_src: Optional[str] = None

# Схема для создания напитка
class DrinkCreate(BaseModel):
    name: str
    ingredients: str
    product_description: str
    global_sale: Optional[int] = None
    section_id: str
    volume_prices: List[DrinkVolumePriceCreate]

# Схема для чтения напитка
class DrinkRead(DrinkCreate):
    id: int
    class Config:
        from_attributes = True  # Для работы с объектами SQLAlchemy/SQLModel

# Схема для создания секции
class SectionCreate(BaseModel):
    id: str
    title: str
    img_src: Optional[str] = None

# Схема для чтения секции
class SectionRead(SectionCreate):
    pass


class SectionWithDrinks(SectionCreate):
    drinks: List[DrinkRead]
    total_drinks: int
    total_pages: int
    current_page: int

class SectionDrinksResponse(BaseModel):
    id: str
    title: str
    drinks: List[DrinkRead]



