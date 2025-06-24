from typing import Optional
from uuid import uuid4

# 2. Библиотеки сторонних пакетов
from fastapi import FastAPI, HTTPException, Depends, Response, Request
from sqlmodel import Session, select, delete
from starlette import status

# 3. Локальные модули
# Зависимости и функции для работы с пользователем
from core.dependencies import  get_user_or_none
from models.auth_models import User

# Модели базы данных
from models.cart_models import Cart, CartItem
from models.models import DrinkVolumePrice

# Схемы для сериализации данных
from schemas.cart import (CartItemCreate, CartRead, CartItemRead)
# База данных
from core.database import get_session


def get_or_create_cart(
        request: Request,
        response: Response,
        session: Session = Depends(get_session),
        current_user: Optional[User] = None
) -> Cart:
    """Объединяет гостевую и пользовательскую корзины при входе"""

    session_key = request.cookies.get("cart_session_key")
    guest_cart = None
    user_cart = None

    # 1. Находим гостевую корзину (если есть)
    if session_key:
        guest_cart = session.exec(
            select(Cart)
            .where(Cart.session_key == session_key)
            .where(Cart.user_id.is_(None))
        ).first()

    # 2. Находим пользовательскую корзину (если пользователь авторизован)
    if current_user:
        user_cart = session.exec(
            select(Cart).where(Cart.user_id == current_user.id)
        ).first()

    # 3. Слияние корзин при входе пользователя
    if current_user and guest_cart and (not user_cart or user_cart.id != guest_cart.id):
        if user_cart:
            # Переносим товары из гостевой корзины в пользовательскую
            guest_items = session.exec(
                select(CartItem).where(CartItem.cart_id == guest_cart.id)
            ).all()

            for item in guest_items:
                existing_item = session.exec(
                    select(CartItem)
                    .where(CartItem.cart_id == user_cart.id)
                    .where(CartItem.drink_volume_price_id == item.drink_volume_price_id)
                ).first()

                if existing_item:
                    existing_item.quantity += item.quantity
                    existing_item.item_subtotal = existing_item.price_original * existing_item.quantity
                    existing_item.item_discount = (existing_item.price_original - existing_item.price_final) * existing_item.quantity
                    existing_item.item_total = existing_item.price_final * existing_item.quantity
                    session.add(existing_item)
                else:
                    item.cart_id = user_cart.id
                    session.add(item)

            session.delete(guest_cart)
            cart = user_cart
        else:
            # Привязываем гостевую корзину к пользователю
            guest_cart.user_id = current_user.id
            cart = guest_cart

        # Удаляем куку гостевой сессии
        response.delete_cookie(
            key="cart_session_key",
            httponly=True,
            secure=True,
            samesite="none",
            domain="graduate-work-backend.onrender.com"
        )

        session.commit()
        update_cart_totals(cart.id, session)
        return cart

    # 4. Возвращаем существующую корзину
    if user_cart:
        return user_cart
    if guest_cart:
        return guest_cart

    # 5. Создаем новую корзину
    new_session_key = str(uuid4())
    cart = Cart(
        session_key=new_session_key,
        user_id=current_user.id if current_user else None,
        cart_subtotal=0,
        cart_discount=0,
        cart_total=0
    )
    session.add(cart)
    session.commit()

    if not current_user:
        response.set_cookie(
            key="cart_session_key",
            value=new_session_key,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            secure=True,
            samesite="none",
            domain="graduate-work-backend.onrender.com"
        )

    return cart



def update_cart_totals(cart_id: int, session: Session):
    cart = session.get(Cart, cart_id)
    if not cart:
        return

    cart_items = session.exec(select(CartItem).where(CartItem.cart_id == cart_id)).all()

    # Пересчитываем общие суммы корзины
    cart.cart_subtotal = sum(item.item_subtotal for item in cart_items)
    cart.cart_discount = sum(item.item_discount for item in cart_items)
    cart.cart_total = sum(item.item_total for item in cart_items)

    session.add(cart)
    session.commit()
    session.refresh(cart)


def setup_cart_endpoints(app: FastAPI):

    # ЭНДПОИНТЫ ДЛЯ РАБОТЫ С КОРЗИНОЙ

    @app.post("/cart/items/", response_model=CartItemRead)
    async def add_to_cart(
            item_data: CartItemCreate,
            request: Request,
            response: Response,
            current_user: Optional[User] = Depends(get_user_or_none),
            session: Session = Depends(get_session)
    ):
        """
        Добавление товара в корзину пользователя.
        Возвращает созданную или обновленную позицию с расчетом всех ценовых показателей.
        """
        # Получение корзины (работает для всех пользователей)
        cart = get_or_create_cart(request, response, session, current_user)

        # Проверка существования товара
        drink_volume_price = session.get(DrinkVolumePrice, item_data.drink_volume_price_id)
        if not drink_volume_price:
            raise HTTPException(status_code=404, detail="Товар не найден")

        # Проверка доступного количества
        if drink_volume_price.quantity < item_data.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно товара на складе. Доступно: {drink_volume_price.quantity}"
            )

        # Поиск существующей позиции в корзине
        existing_item = session.exec(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .where(CartItem.drink_volume_price_id == item_data.drink_volume_price_id)
        ).first()

        # Определяем процент скидки (из объема или глобальный)
        sale_percent = drink_volume_price.sale or drink_volume_price.drink.global_sale or 0
        price_final = round(drink_volume_price.price * (100 - sale_percent) / 100)

        # Обновление количества или создание новой позиции
        if existing_item:
            existing_item.quantity += item_data.quantity
            # Пересчитываем суммы при обновлении количества
            existing_item.item_subtotal = drink_volume_price.price * existing_item.quantity
            existing_item.item_discount = (drink_volume_price.price - price_final) * existing_item.quantity
            existing_item.item_total = price_final * existing_item.quantity
            cart_item = existing_item
        else:
            cart_item = CartItem.create(
                session,
                cart_id=cart.id,
                drink_id=drink_volume_price.drink_id,
                drink_volume_price_id=item_data.drink_volume_price_id,
                quantity=item_data.quantity,
                item_subtotal = drink_volume_price.price * item_data.quantity,
                item_discount = (drink_volume_price.price - price_final) * item_data.quantity,
                item_total = price_final * item_data.quantity
            )
            session.add(cart_item)

        # Корректировка остатков на складе
        drink_volume_price.quantity -= item_data.quantity
        session.add(drink_volume_price)
        session.commit()
        session.refresh(cart_item)

        update_cart_totals(cart.id, session)

        # Формирование ответа
        return CartItemRead.model_validate(cart_item)

    @app.delete("/cart/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def remove_from_cart(
            item_id: int,
            request: Request,
            response: Response,
            current_user: Optional[User] = Depends(get_user_or_none),
            session: Session = Depends(get_session)
    ):
        """Удаление товара из корзины пользователя с возвратом количества на склад"""
        # Находим элемент корзины
        cart_item = session.get(CartItem, item_id)
        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Элемент корзины не найден"
            )

        # Проверяем, что товар принадлежит корзине текущего пользователя
        cart = get_or_create_cart(request, response, session, current_user)
        if not cart or cart_item.cart_id != cart.id:
            raise HTTPException(status_code=403, detail="Нельзя изменить чужую корзину")

        # Находим связанный товар на складе
        drink_volume_price = session.get(DrinkVolumePrice, cart_item.drink_volume_price_id)
        if not drink_volume_price:
            session.delete(cart_item)
            session.commit()
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        try:
            # Возвращаем количество на склад
            drink_volume_price.quantity += cart_item.quantity
            session.add(drink_volume_price)

            # Удаляем элемент из корзины
            session.delete(cart_item)
            session.commit()
            update_cart_totals(cart.id, session)

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при удалении товара из корзины: {str(e)}"
            )


    @app.put("/cart/items/{item_id}/decrement", response_model=CartItemRead)
    async def decrement_item(
            item_id: int,
            request: Request,
            response: Response,
            current_user: Optional[User] = Depends(get_user_or_none),
            session: Session = Depends(get_session)
    ):
        """ Уменьшает количество товара на 1 единицу """
        cart_item = session.get(CartItem, item_id)
        if not cart_item:
            raise HTTPException(status_code=404, detail="Позиция не найдена")

        # Проверка прав доступа
        cart = get_or_create_cart(request, response, session, current_user)
        if not cart or cart_item.cart_id != cart.id:
            raise HTTPException(status_code=403, detail="Нельзя изменить чужую корзину")

        # Получаем связанный товар на складе
        drink_volume_price = session.get(DrinkVolumePrice, cart_item.drink_volume_price_id)

        # Уменьшаем количество в корзине
        cart_item.quantity -= 1

        # Пересчитываем суммы при уменьшении количества
        sale_percent = drink_volume_price.sale or drink_volume_price.drink.global_sale or 0
        price_final = round(drink_volume_price.price * (100 - sale_percent) / 100)

        cart_item.item_subtotal = drink_volume_price.price * cart_item.quantity
        cart_item.item_discount = (drink_volume_price.price - price_final) * cart_item.quantity
        cart_item.item_total = price_final * cart_item.quantity

        # Возвращаем 1 единицу на склад
        if drink_volume_price:
            drink_volume_price.quantity += 1
            session.add(drink_volume_price)

        session.add(cart_item)
        session.commit()
        update_cart_totals(cart.id, session)
        session.refresh(cart_item)

        return CartItemRead.model_validate(cart_item)


    @app.delete("/cart/", status_code=status.HTTP_204_NO_CONTENT)
    async def clear_cart(
            request: Request,
            response: Response,
            current_user: Optional[User] = Depends(get_user_or_none),
            session: Session = Depends(get_session)
    ):
        """Полная очистка корзины пользователя с возвратом всех товаров на склад"""

        # Получаем корзину пользователя
        cart = get_or_create_cart(request, response, session, current_user)
        if not cart:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        try:
            # Получаем все элементы корзины
            cart_items = session.exec(select(CartItem).where(CartItem.cart_id == cart.id)).all()

            # Возвращаем все товары на склад
            for item in cart_items:
                drink_volume_price = session.get(DrinkVolumePrice, item.drink_volume_price_id)
                if drink_volume_price:
                    drink_volume_price.quantity += item.quantity
                    session.add(drink_volume_price)

            # Удаляем все элементы корзины
            session.exec(delete(CartItem).where(CartItem.cart_id == cart.id))
            session.commit()
            update_cart_totals(cart.id, session)

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при очистке корзины: {str(e)}"
            )

    @app.get("/cart/", response_model=CartRead)
    async def get_cart(
            request: Request,
            response: Response,
            current_user: Optional[User] = Depends(get_user_or_none),
            session: Session = Depends(get_session)
    ):
        """
        Получение полного состояния корзины.
        Включает расчет всех ценовых показателей для каждой позиции и общей суммы.
        """
        # Получение корзины пользователя
        cart = get_or_create_cart(request, response, session, current_user)
        cart_items = session.exec(select(CartItem).where(CartItem.cart_id == cart.id)).all()

        # Формирование данных позиции
        items_read = [
            CartItemRead(
                id=item.id,
                cart_id=item.cart_id,
                drink_id=item.drink_id,
                drink_volume_price_id=item.drink_volume_price_id,
                quantity=item.quantity,
                name=item.name,
                img_src=item.img_src,
                volume=item.volume,
                price_original=item.price_original,
                sale=item.sale,
                price_final=item.price_final,
                ingredients=item.ingredients,
                item_subtotal=item.item_subtotal,
                item_discount=item.item_discount,
                item_total=item.item_total
            ) for item in cart_items
        ]

        # Вычисляем общее количество товаров
        cart_quantity = sum(item.quantity for item in cart_items)

        # Рассчитываем общие суммы по корзине
        return CartRead(
            id=cart.id,
            user_id=cart.user_id,
            items=items_read,
            cart_subtotal=cart.cart_subtotal,
            cart_discount=cart.cart_discount,
            cart_total=cart.cart_total,
            cart_quantity=cart_quantity
        )




