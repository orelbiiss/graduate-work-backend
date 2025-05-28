# 1. Стандартные библиотеки
from typing import Dict, Any

# 2. Библиотеки сторонних пакетов
from fastapi import FastAPI, HTTPException, Depends, Query
from sqlmodel import Session, select, func

from models.auth_models import StoreAddress, Address
# Модели базы данных
from models.cart_models import Order, OrderItem
from models.models import DrinkVolumePrice
from schemas.address import StoreAddressRead, AddressRead

# Схемы для сериализации данных
from schemas.cart import (OrderRead, OrderUpdate, OrderStatus)
# База данных
from core.database import get_session


def setup_admin_endpoints(app: FastAPI):

    @app.get("/admin/orders/active-count/", tags=["Admin"], response_model=int)
    async def get_active_orders_count(
            session: Session = Depends(get_session)
    ):
        """Получение количества активных заказов (NEW, ASSEMBLING, ON_THE_WAY)"""

        count = session.exec(
            select(func.count(Order.id)).where(
                Order.status.in_([
                    OrderStatus.NEW,
                    OrderStatus.PROCESSING,
                    OrderStatus.DELIVERING
                ])
            )
        ).one()
        return count

    @app.get("/admin/orders/status-counts/", tags=["Admin"], response_model=Dict[OrderStatus, int])
    async def get_orders_count_by_status(
            session: Session = Depends(get_session)
    ):
        """Получение количества заказов по каждому статусу"""

        status_counts = {}
        for status in OrderStatus:
            count = session.exec(
                select(func.count(Order.id)).where(Order.status == status)
            ).one()
            status_counts[status] = count
        return status_counts

    @app.get("/admin/orders/", response_model=Dict[str, Any], tags=["Admin"])
    async def get_all_orders(
            session: Session = Depends(get_session),
            page: int = Query(1, alias="page", ge=1),
            limit: int = Query(9, alias="limit", ge=1, le=100),
            status: str = Query("all", alias="status")
    ):
        """Получение всех заказов пользователей с пагинацией (админ-панель)"""
        skip = (page - 1) * limit

        base_query = select(Order).order_by(Order.created_at.desc())
        count_query = select(func.count(Order.id))

        if status != "all":
            base_query = base_query.where(Order.status == status)
            count_query = count_query.where(Order.status == status)

        orders = session.exec(base_query.offset(skip).limit(limit)).all()
        total_orders = session.scalar(count_query)

        enriched_orders = []
        for order in orders:
            order_data = order.dict()

            # Добавляем адрес, если есть
            if order.address_id:
                address = session.get(Address, order.address_id)
                order_data["address"] = AddressRead.model_validate(address) if address else None
            else:
                order_data["address"] = None

            # Добавляем магазин, если есть
            if order.store_address_id:
                store_address = session.get(StoreAddress, order.store_address_id)
                order_data["store_address"] = StoreAddressRead.model_validate(store_address) if store_address else None
            else:
                order_data["store_address"] = None

            # Добавляем элементы заказа
            order_items = session.exec(
                select(OrderItem).where(OrderItem.order_id == order.id)
            ).all()

            items_read = []
            for item in order_items:
                drink_volume = session.get(DrinkVolumePrice, item.drink_volume_price_id)
                items_read.append({
                    "id": item.id,
                    "drink_id": item.drink_id,
                    "drink_volume_price_id": item.drink_volume_price_id,
                    "quantity": item.quantity,
                    "volume": item.volume,
                    "price_original": item.price_original,
                    "sale": item.sale,
                    "price_final": item.price_final,
                    "item_subtotal": item.item_subtotal,
                    "item_discount": item.item_discount,
                    "item_total": item.item_total,
                    "name": drink_volume.drink.name if drink_volume else None,
                    "img_src": drink_volume.img_src if drink_volume else None
                })

            order_data["items"] = items_read

            enriched_orders.append(order_data)

        return {"total": total_orders, "orders": enriched_orders}

    @app.patch("/admin/orders/{order_id}", tags=["Admin"], response_model=OrderRead)
    async def update_order_status(
            order_id: int,
            order_update: OrderUpdate,
            session: Session = Depends(get_session)
    ):
        """Обновление статуса заказа"""

        order = session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        if order_update.status:
            order.status = order_update.status

        session.add(order)
        session.commit()
        session.refresh(order)
        return order




