from math import ceil

from fastapi import HTTPException, Depends, File, UploadFile, Form, Query
from sqlalchemy import func
from sqlmodel import Session, select
from typing import List, Optional, Dict
from pathlib import Path
from pydantic import TypeAdapter
import json

from core.s3 import s3_service
from core.translate import generate_section_id
from id_generator import create_with_unique_id
from models.models import Section, Drink, DrinkVolumePrice
from schemas.schemas import SectionRead, DrinkRead, DrinkVolumePriceCreate, SectionWithDrinks, SectionDrinksResponse, DrinkVolumePriceUpdate
from core.database import get_session

def setup_catalog_endpoints(app):
    # Роут для получения всех секций (без напитков)
    @app.get("/sections/", tags=["Section"], response_model=List[SectionRead])
    def get_sections(
            session: Session = Depends(get_session)
    ):
        """Получение всех секций (без напитков)"""
        sections = session.exec(select(Section)).all()
        return sections


    @app.get("/sections/{section_id}", tags=["Section"], response_model=SectionWithDrinks)
    def get_section_by_id(
            section_id: str,  # Изменил на str, так как в SectionCreate id - строка
            page: int = Query(1, ge=1),
            per_page: int = Query(20, ge=1, le=100),
            session: Session = Depends(get_session)
    ):
        """Получение секции с напитками (пагинация по 20 шт)"""
        # Получаем саму секцию
        section = session.get(Section, section_id)
        if not section:
            raise HTTPException(status_code=404, detail="Section not found")

        # Получаем общее количество напитков в секции
        total_drinks = session.exec(
            select(func.count()).select_from(Drink).where(Drink.section_id == section_id)
        ).one()

        # Получаем напитки с пагинацией
        stmt = (
            select(Drink)
            .where(Drink.section_id == section_id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        drinks = session.exec(stmt).all()

        # Преобразуем напитки в формат Pydantic
        drinks_read = []
        for drink in drinks:
            drink_dict = {
                "id": drink.id,
                "name": drink.name,
                "ingredients": drink.ingredients,
                "product_description": drink.product_description,
                "global_sale": drink.global_sale,
                "section_id": drink.section_id,
                "volume_prices": [
                    {
                        "id": vp.id,
                        "img_src": vp.img_src,
                        "volume": vp.volume,
                        "price": vp.price,
                        "quantity": vp.quantity,
                        "sale": vp.sale
                    }
                    for vp in drink.volume_prices
                ]
            }
            drinks_read.append(DrinkRead(**drink_dict))

        total_pages = ceil(total_drinks / per_page)

        return SectionWithDrinks(
            id=section.id,
            title=section.title,
            img_src=section.img_src,
            drinks=drinks_read,
            total_drinks=total_drinks,
            total_pages=total_pages,
            current_page=page
        )

    # Роут для добавления новой секции
    @app.post("/sections", tags=["Section"])
    async def create_section(
        title: str = Form(...),
        image: Optional[UploadFile] = File(None),
        session: Session = Depends(get_session)
    ):
        """Добавление новой секции"""
        section_id = generate_section_id(title)

        # Проверяем, существует ли секция с таким ID
        db_section = session.get(Section, section_id)
        if db_section:
            raise HTTPException(status_code=400, detail="Section ID already exists")

        # Сохраняем изображение, если оно предоставлено
        if image:
            # Генерируем имя файла на основе ID секции
            img_filename = f"{section_id}{Path(image.filename).suffix}"
            img_src = s3_service.upload_file(image, "sections", img_filename)
        else:
            # Используем дефолтное изображение, если фото не добавлено
            img_src = "https://zerop-static-storage.storage.yandexcloud.net/sections/default.webp"

        # Создаем новую секцию
        new_section = Section(
            id=section_id,
            title=title,
            img_src=img_src  # Путь к изображению
        )

        # Добавляем секцию в базу данных
        session.add(new_section)
        session.commit()
        session.refresh(new_section)

        return new_section

    # удаление секции
    @app.delete("/sections/{section_id}", tags=["Section"], response_model=dict)
    async def delete_section(
            section_id: str,  # ID секции для удаления
            session: Session = Depends(get_session)
    ):
        """Удаление секции и всех связанных с ней напитков"""
        # Проверяем существование секции
        section = session.get(Section, section_id)
        if not section:
            raise HTTPException(status_code=404, detail="Секция не найдена")


        # Удаляем изображение секции, если не дефолтное
        if "default.webp" not in section.img_src:
            filename = section.img_src.split("/")[-1]
            s3_service.delete_file("sections", filename)

        # Удаляем саму секцию
        session.delete(section)
        session.commit()

        return {"message": f"Секция {section_id} и все её напитки успешно удалены"}

    # Роут для получения информации о напитке
    @app.get("/product/{drink_id}", tags=["Drinks"], response_model=DrinkRead)
    def get_drink(
            drink_id: int,  # ID напитка
            session: Session = Depends(get_session)
    ):
        """Получение информации о конкретном напитке"""
        # Находим напиток по ID
        drink = session.get(Drink, drink_id)
        if not drink:
            raise HTTPException(status_code=404, detail="Напиток не найден")

        return drink

    # Роут для получения всех напитков
    @app.get("/drinks/", tags=["Drinks"], response_model=List[DrinkRead])
    def get_drinks(
            session: Session = Depends(get_session)
    ):
        """Получение всех напитков"""
        drinks = session.exec(select(Drink)).all()
        return drinks

    @app.get("/drinks/random/", tags=["Drinks"], response_model=Dict[str, SectionDrinksResponse])
    def get_random_drinks_by_section(
            limit: int = Query(10, ge=1, le=100),
            session: Session = Depends(get_session)
    ):
        """Получение случайных напитков, сгруппированных по секциям"""
        # Получаем случайные напитки с информацией о секции
        stmt = (
            select(Drink)
            .join(Section)
            .order_by(func.rand())
            .limit(limit)
        )
        drinks = session.exec(stmt).all()

        # Группируем напитки по секциям
        result = {}
        for drink in drinks:
            section_id = drink.section.id
            if section_id not in result:
                result[section_id] = {
                    "id": section_id,
                    "title": drink.section.title,
                    "drinks": []
                }

            drink_data = {
                "id": drink.id,
                "name": drink.name,
                "ingredients": drink.ingredients,
                "product_description": drink.product_description,
                "global_sale": drink.global_sale,
                "section_id": drink.section_id,
                "volume_prices": [
                    {
                        "id": vp.id,
                        "volume": vp.volume,
                        "price": vp.price,
                        "quantity": vp.quantity,
                        "sale": vp.sale,
                        "img_src": vp.img_src
                    }
                    for vp in drink.volume_prices
                ]
            }
            result[section_id]["drinks"].append(drink_data)

        return result

    # Роут для добавления напитка
    @app.post("/drinks/", tags=["Drinks"], response_model=DrinkRead)
    async def create_drink(
        name: str = Form(...),
        ingredients: str = Form(...),
        product_description: str = Form(...),
        section_id: str = Form(...),
        volume_prices: str = Form(...),  # Принимаем как строку (JSON)
        global_sale: Optional[int] = Form(None),
        image: Optional[UploadFile] = File(None),
        session: Session = Depends(get_session)
    ):
        """Добавление нового напитка"""
        # Проверяем, существует ли секция
        section = session.get(Section, section_id)
        if not section:
            raise HTTPException(status_code=404, detail="Секция не найдена")

        # Декодируем JSON-строку volume_prices в список объектов
        try:
            volume_prices_data = json.loads(volume_prices)
            # Валидируем данные с помощью TypeAdapter
            adapter = TypeAdapter(List[DrinkVolumePriceCreate])
            volume_prices_validated = adapter.validate_python(volume_prices_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Недопустимый формат JSON в volume_prices")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")

        # Создаем новый напиток
        new_drink = create_with_unique_id(
            session=session,
            model=Drink,
            name=name,
            ingredients=ingredients,
            product_description=product_description,
            global_sale=global_sale,
            section_id=section_id
        )
        session.add(new_drink)
        session.commit()
        session.refresh(new_drink)

        # Сохранение изображения
        if image:
            img_filename = f"{new_drink.id}{Path(image.filename).suffix}"
            new_drink.img_src = s3_service.upload_file(image, "products", img_filename)
        else:
            new_drink.img_src = "https://zerop-static-storage.storage.yandexcloud.net/products/default.webp"

        session.commit()

        # Добавляем объемы и цены
        for volume_price in volume_prices_validated:
            new_volume_price = DrinkVolumePrice.create(
                session,
                drink_id=new_drink.id,
                volume=volume_price.volume,
                price=volume_price.price,
                quantity=volume_price.quantity,
                sale=volume_price.sale,
                img_src=new_drink.img_src
            )
            session.add(new_volume_price)

        session.commit()
        return new_drink


    # Роут для обновления напитка (только глобальные поля)
    @app.patch("/drinks/{drink_id}", tags=["Drinks"], response_model=DrinkRead)
    async def update_drink(
            drink_id: int,
            name: Optional[str] = Form(None),
            ingredients: Optional[str] = Form(None),
            product_description: Optional[str] = Form(None),
            section_id: Optional[str] = Form(None),
            global_sale: Optional[int] = Form(None),
            image: Optional[UploadFile] = File(None),
            session: Session = Depends(get_session)
    ):
        """Обновление глобальных данных напитка (без объемов)"""

        # Получаем напиток по ID
        db_drink = session.get(Drink, drink_id)
        if not db_drink:
            raise HTTPException(status_code=404, detail="Напиток не найден")

        # Обновляем поля, если они предоставлены
        if name is not None:
            db_drink.name = name
        if ingredients is not None:
            db_drink.ingredients = ingredients
        if product_description is not None:
            db_drink.product_description = product_description
        if global_sale is not None:
            db_drink.global_sale = global_sale

        # Если предоставлен section_id, проверяем, существует ли секция
        if section_id is not None:
            section = session.get(Section, section_id)
            if not section:
                raise HTTPException(status_code=404, detail="Секция не найдена")
            db_drink.section_id = section_id

        # Работа с изображением
        if image:
            # Если предоставлено новое изображение, удаляем старое (если оно не дефолтное)
            if db_drink.img_src and "default.webp" not in db_drink.img_src:
                old_filename = db_drink.img_src.split("/")[-1]
                s3_service.delete_file("products", old_filename)

            # Сохраняем новое изображение
            img_filename = f"{db_drink.id}{Path(image.filename).suffix}"
            db_drink.img_src = s3_service.upload_file(image, "products", img_filename)

            # Обновляем изображение для всех объемов, которые используют изображение напитка
            for volume in db_drink.volume_prices:
                if not volume.img_src or "default.webp" in volume.img_src:
                    volume.img_src = db_drink.img_src

        session.commit()
        session.refresh(db_drink)

        return db_drink


    # Роут для удаления напитка
    @app.delete("/drinks/{drink_id}", tags=["Drinks"], response_model=dict)
    async def delete_drink(
        drink_id: int,  # ID напитка, который нужно удалить
        session: Session = Depends(get_session)  # Сессия базы данных
    ):
        """Удаление напитка"""

        # Находим напиток по ID
        db_drink = session.get(Drink, drink_id)
        if not db_drink:
            # Если напиток не найден, возвращаем ошибку 404
            raise HTTPException(status_code=404, detail="Напиток не найден")


        # Удаляем основное изображение напитка, если оно не является дефолтным
        if db_drink.img_src and "default.webp" not in db_drink.img_src:
            filename = db_drink.img_src.split("/")[-1]
            s3_service.delete_file("products", filename)

        # Удаляем сам напиток из базы данных
        session.delete(db_drink)
        session.commit()

        # Возвращаем сообщение об успешном удалении
        return {"message": "Напиток успешно удален"}

    # Роут для обновления конкретного объема напитка
    @app.patch("/drinks/{drink_id}/volumes/{volume_id}", tags=["Drinks"], response_model=DrinkVolumePrice)
    async def update_drink_volume(
            drink_id: int,
            volume_id: int,
            volume_data: DrinkVolumePriceUpdate,
            image: Optional[UploadFile] = File(None),
            session: Session = Depends(get_session)
    ):
        """Обновление конкретного объема напитка"""

        # Проверяем существование напитка
        drink = session.get(Drink, drink_id)
        if not drink:
            raise HTTPException(status_code=404, detail="Напиток не найден")

        # Находим конкретный объем
        volume_price = session.get(DrinkVolumePrice, volume_id)
        if not volume_price or volume_price.drink_id != drink_id:
            raise HTTPException(status_code=404, detail="Объем не найден для этого напитка")

        # Обновляем поля, если они предоставлены
        if volume_data.volume is not None:
            volume_price.volume = volume_data.volume
        if volume_data.price is not None:
            volume_price.price = volume_data.price
        if volume_data.quantity is not None:
            volume_price.quantity = volume_data.quantity
        if volume_data.sale is not None:
            volume_price.sale = volume_data.sale

        # Работа с изображением
        if image:
            # Удаляем старое изображение, если оно не дефолтное
            if volume_price.img_src and "default.webp" not in volume_price.img_src:
                old_filename = volume_price.img_src.split("/")[-1]
                s3_service.delete_file("products/volumes", old_filename)

            # Сохраняем новое изображение
            img_filename = f"{drink_id}_{volume_id}{Path(image.filename).suffix}"
            volume_price.img_src = s3_service.upload_file(image, "products/volumes", img_filename)

        session.commit()
        session.refresh(volume_price)

        return volume_price

    # Роут для добавления нового объема к напитку
    @app.post("/drinks/{drink_id}/volumes/", tags=["Drinks"], response_model=DrinkVolumePrice)
    async def add_drink_volume(
            drink_id: int,
            volume_data: DrinkVolumePriceCreate,
            image: Optional[UploadFile] = File(None),
            session: Session = Depends(get_session)
    ):
        """Добавление нового объема к напитку"""

        # Проверяем существование напитка
        drink = session.get(Drink, drink_id)
        if not drink:
            raise HTTPException(status_code=404, detail="Напиток не найден")

        # Создаем новый объем
        new_volume = DrinkVolumePrice(
            drink_id=drink_id,
            volume=volume_data.volume,
            price=volume_data.price,
            quantity=volume_data.quantity,
            sale=volume_data.sale,
            img_src=drink.img_src  # Используем изображение напитка по умолчанию
        )

        # Если предоставлено изображение
        if image:
            # Генерируем уникальный ID для нового объема
            new_volume_id = create_with_unique_id(session, DrinkVolumePrice)
            img_filename = f"{drink_id}_{new_volume_id}{Path(image.filename).suffix}"
            new_volume.img_src = s3_service.upload_file(image, "products/volumes", img_filename)

        session.add(new_volume)
        session.commit()
        session.refresh(new_volume)

        return new_volume

    # Роут для удаления конкретного объема
    @app.delete("/drinks/{drink_id}/volumes/{volume_id}", tags=["Drinks"], response_model=dict)
    async def delete_drink_volume(
            drink_id: int,
            volume_id: int,
            session: Session = Depends(get_session)
    ):
        """Удаление конкретного объема напитка"""

        # Проверяем существование напитка
        drink = session.get(Drink, drink_id)
        if not drink:
            raise HTTPException(status_code=404, detail="Напиток не найден")

        # Находим конкретный объем
        volume_price = session.get(DrinkVolumePrice, volume_id)
        if not volume_price or volume_price.drink_id != drink_id:
            raise HTTPException(status_code=404, detail="Объем не найден для этого напитка")

        # Удаляем изображение, если оно не дефолтное
        if volume_price.img_src and "default.webp" not in volume_price.img_src:
            filename = volume_price.img_src.split("/")[-1]
            s3_service.delete_file("products/volumes", filename)

        # Удаляем объем
        session.delete(volume_price)
        session.commit()

        return {"message": "Объем напитка успешно удален"}
