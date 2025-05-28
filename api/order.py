# 1. Стандартные библиотеки
from datetime import datetime, UTC, date
from typing import List, Dict, Optional, Any

# 2. Библиотеки сторонних пакетов
from fastapi import FastAPI, HTTPException, Depends, Response, Query
from sqlmodel import Session, select, func, delete, Field
from starlette import status

from core.delivery_slots import ensure_slots_for_date
# 3. Локальные модули
# Зависимости и функции для работы с пользователем
from core.dependencies import get_current_user

# Модели базы данных
from models.auth_models import Address, StoreAddress, UserRole, User
from models.cart_models import Cart, CartItem, Order, OrderItem, DeliveryTimeSlot, DeliveryTimeSlotStatus, DeliveryInfo
from models.models import DrinkVolumePrice, Drink

# Схемы для сериализации данных
from schemas.address import AddressRead, StoreAddressRead
from schemas.cart import (OrderRead, OrderStatus, DeliveryType, OrderItemRead, OrderCreateResponse, OrderCreateRequest)
from schemas.schemas import DrinkRead  # Импорт новой схемы
# База данных
from core.database import get_session


def setup_order_endpoints(app: FastAPI):

    # ЭНДПОИНТЫ ДЛЯ РАБОТЫ С ЗАКАЗАМИ

    @app.post("/orders/", response_model=OrderCreateResponse)
    async def create_order(
            order_data: OrderCreateRequest,
            current_user: int = Depends(get_current_user),
            session: Session = Depends(get_session)
    ):
        """Создание нового заказа с сохранением данных доставки в таблицу DeliveryInfo"""

        # 1. Проверка корзины и товаров
        cart = session.exec(select(Cart).where(Cart.user_id == current_user.id)).first()
        if not cart:
            raise HTTPException(status_code=400, detail="Корзина не найдена")

        cart_items = session.exec(select(CartItem).where(CartItem.cart_id == cart.id)).all()
        if not cart_items:
            raise HTTPException(status_code=400, detail="Корзина пуста")

        # 2. Расчет сумм заказа
        order_subtotal = sum(item.item_subtotal for item in cart_items)
        order_discount = sum(item.item_discount for item in cart_items)
        order_total = order_subtotal - order_discount + order_data.delivery_price

        # 3. Получение данных пользователя
        user = session.get(User, current_user.id)
        customer_name = f"{user.last_name} {user.first_name}".strip()
        customer_phone = user.phone

        # 4. Обработка доставки
        address = None
        store_address = None
        delivery_time = None
        full_address = None

        if order_data.delivery_type == DeliveryType.COURIER:
            # Проверка адреса доставки
            address = session.exec(
                select(Address)
                .where(Address.user_id == current_user.id)
                .order_by(Address.is_default.desc())
            ).first()
            if not address:
                raise HTTPException(status_code=400, detail="Не указан адрес доставки")

            # Формирование полного адреса
            full_address = (
                    (address.full_address or '') +
                    (f", кв. {address.apartment}" if address.apartment else '') +
                    (f", домофон {address.intercom}" if address.intercom else '') +
                    (f", подъезд {address.entrance}" if address.entrance else '') +
                    (f", этаж {address.floor}" if address.floor else '')
            ).strip(', ')

            # Проверка временного слота
            if not order_data.time_slot_id:
                raise HTTPException(400, "Не указан ID временного слота")

            slot = session.get(DeliveryTimeSlot, order_data.time_slot_id)
            if not slot:
                raise HTTPException(400, "Указанный слот доставки не найден")

            if slot.date != order_data.delivery_date:
                raise HTTPException(400, "Слот не соответствует выбранной дате")

            if slot.current_orders >= slot.max_orders:
                raise HTTPException(400, "Выбранный слот уже заполнен")

            # Резервирование слота
            slot.current_orders += 1
            if slot.current_orders >= slot.max_orders:
                slot.status = DeliveryTimeSlotStatus.UNAVAILABLE
            session.add(slot)

            delivery_time = slot.time_slot

        elif order_data.delivery_type == DeliveryType.PICKUP:
            # Проверка магазина самовывоза
            if not order_data.store_address_id:
                raise HTTPException(status_code=400, detail="Не выбран магазин самовывоза")

            store_address = session.get(StoreAddress, order_data.store_address_id)
            if not store_address:
                raise HTTPException(status_code=400, detail="Магазин не найден")

        # 5. Создание заказа (Order)
        order = Order.create(
            session,
            user_id=current_user.id,
            delivery_type=order_data.delivery_type,
            address_id=address.id if address else None,
            store_address_id=store_address.id if store_address else None,
            order_subtotal=order_subtotal,
            order_discount=order_discount,
            order_total=order_total,
            status=OrderStatus.NEW,
            created_at=datetime.now(UTC)
        )
        session.add(order)
        session.flush()  # Получаем ID заказа

        # 6. Создание записи о доставке (DeliveryInfo)
        delivery_info = DeliveryInfo.create(
            session,
            order_id=order.id,
            time_slot_id=order_data.time_slot_id if order_data.delivery_type == DeliveryType.COURIER else None,
            full_address=full_address if order_data.delivery_type == DeliveryType.COURIER else None,
            delivery_comment=order_data.delivery_comment,
            delivery_date=order_data.delivery_date if order_data.delivery_type == DeliveryType.COURIER else None,
            delivery_time=delivery_time if order_data.delivery_type == DeliveryType.COURIER else None,
            customer_name=customer_name,
            customer_phone=customer_phone,
            delivery_price=order_data.delivery_price
        )
        session.add(delivery_info)

        # 7. Перенос товаров в заказ
        for item in cart_items:
            order_item = OrderItem.create(
                session,
                order_id=order.id,
                drink_id=item.drink_id,
                drink_volume_price_id=item.drink_volume_price_id,
                quantity=item.quantity,
                volume=item.drink_volume_price.volume,
                price_original=item.drink_volume_price.price,
                sale=item.drink_volume_price.sale or item.drink_volume_price.drink.global_sale or 0,
                price_final=item.price_final,
                item_subtotal=item.item_subtotal,
                item_discount=item.item_discount,
                item_total=item.item_total,
            )
            session.add(order_item)

        # 8. Очистка корзины
        session.exec(delete(CartItem).where(CartItem.cart_id == cart.id))
        session.commit()

        # 9. Формирование ответа
        return {
            "id": order.id,
            "order_total": order_total,
            "status": order.status,
            "delivery_type": order_data.delivery_type,
            "created_at": order.created_at
        }

    @app.get("/orders/{order_id}/items", response_model=List[OrderItemRead])
    def get_order_items(
            order_id: int,
            current_user: dict = Depends(get_current_user),
            session: Session = Depends(get_session)
    ):
        """Получить список товаров в заказе"""
        order = session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        if order.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")

        items = session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()

        # Формируем ответ с картинками и названиями
        result = []
        for item in items:
            drink_volume = session.get(DrinkVolumePrice, item.drink_volume_price_id)
            if not drink_volume:
                continue
            result.append(OrderItemRead(
                **item.dict(),
                name=drink_volume.drink.name,
                img_src=drink_volume.img_src or drink_volume.drink.img_src
            ))

        return result

    @app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_order(
            order_id: int,
            current_user: int = Depends(get_current_user),
            session: Session = Depends(get_session)
    ):
        """Удаление заказа"""
        # Получаем заказ из базы данных
        order = session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        # Проверяем права доступа
        if current_user.role != UserRole.ADMIN and order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Нельзя удалить чужой заказ")

        # Для обычных пользователей проверяем статус заказа
        if current_user.role == UserRole.USER and order.status != OrderStatus.NEW:
            raise HTTPException(
                status_code=400,
                detail="Можно удалять только заказы со статусом 'NEW'"
            )

        try:
            # Удаляем связанные товары в заказе
            session.exec(delete(OrderItem).where(OrderItem.order_id == order_id))

            # Удаляем сам заказ
            session.delete(order)
            session.commit()

            return Response(status_code=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при удалении заказа: {str(e)}"
            )

    @app.get("/orders/my", response_model=Dict[str, Any])
    async def get_my_orders(
            current_user: int = Depends(get_current_user),
            session: Session = Depends(get_session),
            page: int = Query(1, ge=1),
            limit: int = Query(9, ge=1, le=100)
    ):
        """Получение списка заказов пользователя с пагинацией"""
        skip = (page - 1) * limit

        orders_query = select(Order).where(
            Order.user_id == current_user.id
        ).order_by(
            Order.created_at.desc()
        ).offset(skip).limit(limit)

        count_query = select(func.count()).where(Order.user_id == current_user.id)

        orders = session.exec(orders_query).all()
        total_orders = session.scalar(count_query)

        result = []
        for order in orders:
            # Получаем элементы заказа
            order_items = session.exec(
                select(OrderItem).where(OrderItem.order_id == order.id)
            ).all()

            items_read = []
            for item in order_items:
                drink_volume = session.get(DrinkVolumePrice, item.drink_volume_price_id)
                items_read.append(OrderItemRead(
                    **item.dict(),
                    name=drink_volume.drink.name,
                    img_src=drink_volume.img_src or drink_volume.drink.img_src
                ))

            # Получаем информацию о доставке из новой таблицы
            delivery_info = session.exec(
                select(DeliveryInfo).where(DeliveryInfo.order_id == order.id)
            ).first()

            # Формируем ответ в старом формате, подставляя данные из DeliveryInfo
            order_data = order.dict()
            if delivery_info:
                order_data.update({
                    "full_address": delivery_info.full_address,
                    "delivery_comment": delivery_info.delivery_comment,
                    "delivery_date": delivery_info.delivery_date,
                    "delivery_time": delivery_info.delivery_time,
                    "customer_name": delivery_info.customer_name,
                    "customer_phone": delivery_info.customer_phone,
                    "delivery_price": delivery_info.delivery_price
                })

            # Получаем адресные данные
            address = session.get(Address, order.address_id) if order.address_id else None
            store_address = session.get(StoreAddress, order.store_address_id) if order.store_address_id else None

            order_data.update({
                "items": items_read,
                "address": AddressRead.model_validate(address).dict() if address else None,
                "store_address": StoreAddressRead.model_validate(store_address).dict() if store_address else None
            })

            result.append(order_data)

        return {
            "total": total_orders,
            "orders": result
        }

    @app.get("/orders/my/drinks", response_model=Dict[str, Any])
    async def get_my_purchased_drinks(
            current_user: int = Depends(get_current_user),
            session: Session = Depends(get_session),
            page: int = Query(1, ge=1),
            limit: int = Query(9, ge=1, le=100)
    ):
        """Получение уникальных напитков пользователя с полной информацией"""
        skip = (page - 1) * limit

        # Получаем ID всех напитков, которые пользователь когда-либо заказывал
        drink_ids = session.scalars(
            select(OrderItem.drink_id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.user_id == current_user.id)
            .distinct()
        ).all()

        if not drink_ids:
            return {"total": 0, "drinks": []}

        # Общее количество уникальных напитков
        total = len(drink_ids)

        # Получаем полную информацию о напитках с пагинацией
        drinks = session.exec(
            select(Drink)
            .where(Drink.id.in_(drink_ids))
            .offset(skip)
            .limit(limit)
        ).all()

        # Формируем ответ с полной информацией о напитках
        result = []
        for drink in drinks:
            # Получаем все варианты объема/цены для напитка
            volume_prices = session.exec(
                select(DrinkVolumePrice)
                .where(DrinkVolumePrice.drink_id == drink.id)
            ).all()

            # Используем новую схему DrinkRead для сериализации
            drink_data = DrinkRead(
                id=drink.id,
                name=drink.name,
                ingredients=drink.ingredients,
                product_description=drink.product_description,
                global_sale=drink.global_sale,
                section_id=drink.section_id,
                volume_prices=[
                    {
                        "id": vp.id,
                        "img_src": vp.img_src or drink.img_src,
                        "volume": vp.volume,
                        "price": vp.price,
                        "quantity": vp.quantity,
                        "sale": vp.sale
                    }
                    for vp in volume_prices
                ]
            )
            result.append(drink_data)

        return {
            "total": total,
            "drinks": result
        }

    @app.get("/delivery/slots/")
    async def get_delivery_slots(
            delivery_date: date,
            db: Session = Depends(get_session)
    ):
        """Получение слотов на указанную дату (с автоматической генерацией при первом запросе)"""
        # Проверяем существующие слоты
        existing_slots = db.exec(
            select(DeliveryTimeSlot)
            .where(DeliveryTimeSlot.date == delivery_date)
        ).all()

        # Если слотов нет — генерируем
        if not existing_slots:
            existing_slots = ensure_slots_for_date(db, delivery_date)

        return [{
            "id": slot.id,
            "time_slot": slot.time_slot,
            "available": slot.max_orders - slot.current_orders,
            "status": slot.status.value
        } for slot in existing_slots]