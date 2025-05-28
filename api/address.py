from fastapi import FastAPI, HTTPException, Depends, status
from sqlmodel import Session, select
from typing import List

from core.dependencies import get_current_user
from models.auth_models import Address, User, StoreAddress
from models.cart_models import Order
from schemas.address import (AddressCreate, AddressRead, AddressUpdate, StoreAddressUpdate,
                             StoreAddressRead, StoreAddressCreate)
from core.database import get_session



def setup_address_endpoints(app: FastAPI):

    # Получение всех адресов текущего пользователя
    @app.get("/addresses/", tags=["Addresses"], response_model=List[AddressRead])
    async def get_user_addresses(
            current_user: int = Depends(get_current_user),
            session: Session = Depends(get_session)
    ):
        """
        Получение всех адресов текущего пользователя
        Только авторизованные пользователи могут просматривать свои адреса
        """
        addresses = session.exec(
            select(Address).where(Address.user_id == current_user.id)
        ).all()
        return addresses

    @app.get("/addresses/{address_id}", tags=["Addresses"], response_model=AddressRead)
    async def get_address(
            address_id: int,
            current_user: int = Depends(get_current_user),
            session: Session = Depends(get_session)
    ):
        """Получение конкретного адреса по ID"""

        address = session.get(Address, address_id)

        # Если адрес не найден — ошибка
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Адрес не найден"
            )

        # Если не админ и не владелец — доступ запрещён
        if current_user.role != "admin" and address.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет доступа к этому адресу"
            )

        return address

    # Создание нового адреса
    @app.post("/addresses/", tags=["Addresses"], response_model=AddressRead, status_code=status.HTTP_201_CREATED)
    async def create_address(
            address_data: AddressCreate,
            current_user: int = Depends(get_current_user),  # Только для авторизованных
            session: Session = Depends(get_session)
    ):
        """Создание нового адреса для авторизованного пользователя"""
        # Проверяем, существует ли уже такой адрес у пользователя
        existing_address = session.exec(
            select(Address)
            .where(Address.user_id == current_user.id)
            .where(Address.street == address_data.street)
            .where(Address.house == address_data.house)
            .where(Address.apartment == address_data.apartment)
        ).first()
        if existing_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="адрес не может быть добавлен повторно"
            )

        # Проверяем, есть ли уже адреса у пользователя
        user_addresses = session.exec(
            select(Address).where(Address.user_id == current_user.id)
        ).all()

        # Если адрес помечен как основной или это первый адрес пользователя
        if address_data.is_default or not user_addresses:
            # Сбрасываем флаг is_default у всех адресов пользователя
            for addr in user_addresses:
                addr.is_default = False
                session.add(addr)

            # Гарантируем, что новый адрес будет основным
            address_data.is_default = True

        # Создаем новый адрес
        address = Address.create(
            session,
            **address_data.model_dump(exclude_unset=True),
            user_id=current_user.id  # ID пользователя берем из аутентификации
        )

        try:
            session.add(address)
            session.commit()
            session.refresh(address)
            return address
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="не удалось создать адрес"
            )

    # Обновление адреса
    @app.patch("/addresses/{address_id}", tags=["Addresses"], response_model=AddressRead)
    async def update_address(
            address_id: int,
            address_data: AddressUpdate,
            current_user: int = Depends(get_current_user),  # Проверка прав
            session: Session = Depends(get_session)
    ):
        """Обновление данных адреса """

        address = session.get(Address, address_id)
        if not address or address.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Адрес не найден или у вас нет прав для его изменения"
            )

        # Если адрес становится основным
        if address_data.is_default == True:
            existing_addresses = session.exec(
                select(Address)
                .where(Address.user_id == current_user.id)
                .where(Address.id != address_id)
            ).all()
            for addr in existing_addresses:
                addr.is_default = False
                session.add(addr)

        # Обновляем только переданные поля
        update_data = address_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(address, field, value)

        session.add(address)
        session.commit()
        session.refresh(address)
        return address

    # Удаление адреса с автоматическим назначением нового основного
    @app.delete("/addresses/{address_id}",
                tags=["Addresses"],
                status_code=status.HTTP_204_NO_CONTENT)
    async def delete_address(
            address_id: int,
            current_user: User = Depends(get_current_user),
            session: Session = Depends(get_session)
    ):
        """Удаление адреса пользователя с автоматическим назначением нового основного адреса при необходимости"""

        # Получаем адрес с проверкой принадлежности пользователю
        address = session.exec(
            select(Address)
            .where(Address.id == address_id)
            .where(Address.user_id == current_user.id)
        ).first()

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Адрес не найден или у вас нет прав для его удаления"
            )

        # Запоминаем, был ли адрес основным
        was_default = address.is_default

        try:
            # Удаляем адрес
            session.delete(address)

            # Если удаляли основной адрес - ищем новый
            if was_default:
                # Находим последний созданный адрес пользователя (кроме удаляемого)
                new_default = session.exec(
                    select(Address)
                    .where(Address.user_id == current_user.id)
                    .where(Address.id != address_id)
                    .order_by(Address.created_at.desc())
                    .limit(1)
                ).first()

                # Если нашли - делаем его основным
                if new_default:
                    new_default.is_default = True
                    session.add(new_default)

            session.commit()
            return {"message": "Адрес успешно удален"}

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при удалении адреса: {str(e)}"
            )

    ###################
    # АДРЕСА МАГАЗИНОВ
    ###################

    # Добавление нового адреса магазина
    @app.post("/store-addresses/", tags=["Store Addresses"], response_model=StoreAddressRead)
    async def create_store_address(
            address_data: StoreAddressCreate,
            session: Session = Depends(get_session)
    ):
        """Добавление нового адреса магазина."""

        address = StoreAddress.create(session, **address_data.model_dump())
        session.add(address)
        session.commit()
        session.refresh(address)
        return address

    # Получение всех адресов магазинов
    @app.get("/store-addresses/", tags=["Store Addresses"], response_model=List[StoreAddressRead])
    async def get_all_store_addresses(
            session: Session = Depends(get_session)
    ):

        """Получение списка всех адресов магазинов."""

        addresses = session.exec(select(StoreAddress)).all()
        return addresses

    # Получение адреса магазина по ID
    @app.get("/store-addresses/{address_id}", tags=["Store Addresses"], response_model=StoreAddressRead)
    async def get_store_address(address_id: int, session: Session = Depends(get_session)):
        """
        Получение одного адреса магазина по его ID.
        Используется для просмотра деталей конкретного адреса.
        """
        address = session.get(StoreAddress, address_id)
        if not address:
            raise HTTPException(status_code=404, detail="Адрес не найден")
        return address

    # Обновление существующего адреса
    @app.patch("/store-addresses/{address_id}", tags=["Store Addresses"], response_model=StoreAddressRead)
    async def update_store_address(
            address_id: int,
            address_data: StoreAddressUpdate,
            session: Session = Depends(get_session)
    ):
        """Обновление информации об адресе магазина."""

        address = session.get(StoreAddress, address_id)
        if not address:
            raise HTTPException(status_code=404, detail="Адрес не найден")

        for field, value in address_data.model_dump(exclude_unset=True).items():
            setattr(address, field, value)

        session.add(address)
        session.commit()
        session.refresh(address)
        return address

    # Удаление адреса магазина
    @app.delete("/store-addresses/{address_id}", tags=["Store Addresses"])
    async def delete_store_address(address_id: int, session: Session = Depends(get_session)):

        """Удаление адреса магазина по ID."""

        address = session.get(StoreAddress, address_id)
        if not address:
            raise HTTPException(status_code=404, detail="Адрес не найден")

        session.delete(address)
        session.commit()
        return {"detail": "Адрес успешно удален"}

