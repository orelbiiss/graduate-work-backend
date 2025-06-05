# 1. Стандартные библиотеки
from datetime import datetime, timedelta, UTC

# 2. Библиотеки сторонних пакетов
from fastapi import Depends, HTTPException, Response, Request, Form, BackgroundTasks
from sqlmodel import Session, select, func, delete

from api.cart import update_cart_totals
# 3. Локальные модули
from api.password import hash_password, verify_password
from api.verification import send_verification_email, generate_verification_token

# Модели базы данных
from models.auth_models import User, UserRole, Address, EmailVerificationToken, UnverifiedUser, UserSession
from models.cart_models import OrderItem, Order, CartItem, Cart
from models.models import DrinkVolumePrice, Drink

# Схемы для сериализации данных
from schemas.auth import UserCreate, UserRead, UserLogin, UserUpdate

# Конфигурация и зависимости
from core.config import settings
from core.database import get_session
from core.dependencies import get_current_user, get_role_from_token
from core.tokens import create_access_token, set_jwt_cookie, create_refresh_token


def setup_auth_endpoints(app):


    # КАТЕГОРИЯ: РЕГИСТРАЦИЯ И АУТЕНТИФИКАЦИЯ

    # Регистрация нового пользователя
    @app.post("/auth/signup", tags=["Registration/Authentication"])
    async def signup_user(
            user: UserCreate,
            background_tasks: BackgroundTasks,
            session: Session = Depends(get_session)
    ):
        """Регистрация нового пользователя"""
        errors = []
        # проверка на доступность email в основной таблице user
        existing_user = session.exec(select(User).where(User.email == user.email)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Пользователь с таким e-mail уже зарегистрирован")

        # проверка на доступность email в таблице неподтвержденных пользователей
        existing_unverified = session.exec(select(UnverifiedUser).where(UnverifiedUser.email == user.email)).first()
        if existing_unverified:
            if existing_unverified.token_expires.replace(tzinfo=UTC) > datetime.now(UTC):
                raise HTTPException(
                    status_code=400,
                    detail="На этот email уже отправлено письмо с подтверждением. Пожалуйста, проверьте вашу почту."
                )
            # Удаляем просроченную запись
            session.delete(existing_unverified)
            session.commit()

        # Хешируем пароль перед сохранением
        hashed_password = hash_password(user.password)

        # Проверяем, не используется ли пароль другим пользователем
        password_exists = session.exec(
            select(User).where(User.hashed_password == hashed_password)
        ).first()
        if password_exists:
            raise HTTPException(status_code=400, detail="Пароль уже используется другим пользователем")

        # Если есть ошибки, возвращаем их
        if errors:
            raise HTTPException(status_code=422, detail=errors)

        # Валидация телефона (добавляем + при необходимости)
        if user.phone and not user.phone.startswith('+'):
            user.phone = f"+{user.phone}"

        user_role = user.role if user.role else UserRole.USER

        # Создаем объект пользователя для админов без верификации
        if user_role == UserRole.ADMIN:
            new_user = User.create(
                session,
                email=user.email,
                hashed_password=hashed_password,
                first_name=user.first_name,
                last_name=user.last_name,
                birth_date=user.birth_date,
                middle_name=user.middle_name,
                gender=user.gender,
                phone=user.phone,
                role=user_role,
                is_active=True
            )

            session.add(new_user)
            session.commit()
            return {
                "id": new_user.id,
                "message": "Пользователь успешно зарегистрирован. Роль администратора не требует верификации."
            }

        # Для обычных пользователей - сохраняем в UnverifiedUser
        verification_token = generate_verification_token()
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        unverified_user = UnverifiedUser.create(
            session,
            email=user.email,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            birth_date=user.birth_date,
            middle_name=user.middle_name,
            gender=user.gender,
            phone=user.phone,
            role=user_role,
            verification_token=verification_token,
            token_expires=expires_at
        )

        # сохранение в EmailVerificationToken
        email_token = EmailVerificationToken.create(
            session,
            email=user.email,
            token=verification_token,
            expires_at=expires_at,
            is_used=False
        )

        session.add(unverified_user)
        session.add(email_token)

        session.commit()

        # Отправка письма с подтверждением
        await send_verification_email(
            email=user.email,
            token=verification_token,
            background_tasks=background_tasks,
            username=f"{user.first_name} {user.last_name}"
        )

        return {
            "message": "Письмо с подтверждением отправлено на ваш email"
        }


    # Аутентификация пользователя (устанавливает JWT в куки)
    @app.post("/auth/signin", tags=["Registration/Authentication"], response_model=UserRead)
    async def signin_user(
            request: Request,
            response: Response,
            user_data: UserLogin,
            session: Session = Depends(get_session)
    ):

        """Аутентификация с проверкой верификации email"""

        # Ищем пользователя по email
        user = session.exec(select(User).where(User.email == user_data.email)).first()
        if not user:
            raise HTTPException(status_code=400, detail="Пользователь не найден")

        # Проверяем пароль
        if not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Неверный пароль")

        # Создаем новую сессию
        refresh_token_cookie = create_refresh_token()
        user_session = UserSession(
            user_id=user.id,
            refresh_token=refresh_token_cookie,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host
        )
        session.add(user_session)

        # Обновляем время последнего входа
        user.last_login = datetime.now(UTC)
        session.add(user)
        session.commit()

        # Генерируем токены
        access_token = create_access_token({"sub": user.email, "role": user.role})
        set_jwt_cookie(response, access_token, refresh_token_cookie)

        return UserRead.model_validate(user)

    # Выход пользователя (удаляет JWT куку)
    @app.post("/auth/signout", tags=["Registration/Authentication"])
    async def signout_user(
            request: Request,
            response: Response,
            session: Session = Depends(get_session),
            current_user: User = Depends(get_current_user)
    ):
        """Завершение сеанса пользователя с удалением JWT куки"""

        refresh_token_cookie = request.cookies.get("refresh_token")
        if refresh_token_cookie:
            # Удаляем сессию из БД
            session.exec(
                delete(UserSession)
                .where(UserSession.refresh_token == refresh_token_cookie)
                .where(UserSession.user_id == current_user.id)
            )
            session.commit()

        # Очищаем куки
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return {"message": "Успешный выход"}

    # ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ

    # Получение данных текущего пользователя
    @app.get("/user/profile", tags=["User Profile"], response_model=UserRead)
    async def get_current_user_data(
            current_user: User = Depends(get_current_user)
    ):
        """Получение данных текущего пользователя"""

        return current_user

    # Обновление профиля пользователя (без пароля)
    @app.patch("/user/profile", tags=["User Profile"], response_model=UserRead)
    async def update_user_data(
            user_update: UserUpdate,
            session: Session = Depends(get_session),
            current_user: User = Depends(get_current_user)
    ):
        """Обновление профиля пользователя"""

        existing_user = session.exec(
            select(User).where(User.id == current_user.id)
        ).first()

        if not existing_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if user_update.role and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Нет прав на изменение роли")

        update_data = user_update.model_dump(exclude_unset=True, exclude={"password"})

        for field, value in update_data.items():
            if hasattr(existing_user, field):
                setattr(existing_user, field, value)

        session.add(existing_user)
        session.commit()
        session.refresh(existing_user)

        return UserRead.model_validate(existing_user)



    @app.delete("/user/profile", tags=["User Profile"], response_model=dict)
    async def delete_user_account(
            password: str = Form(...),
            session: Session = Depends(get_session),
            current_user: User = Depends(get_current_user)
    ):
        """Удаление аккаунта текущего пользователя со всеми связанными данными"""

        # Проверка пароля
        if not verify_password(password, current_user.hashed_password):
            raise HTTPException(status_code=401, detail="Неверный пароль")

        # Получаем полный объект пользователя из БД
        db_user = session.get(User, current_user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Проверка для администраторов
        if db_user.role == UserRole.ADMIN:
            admin_count = session.exec(
                select(func.count()).where(
                    User.role == UserRole.ADMIN,
                    User.id != db_user.id
                )
            ).first()
            if admin_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Невозможно удалить последнего администратора"
                )

        # Удаление связанных данных (каскадное удаление)

        # 1. Удаление адресов пользователя
        addresses = session.exec(
            select(Address).where(Address.user_id == db_user.id)
        ).all()
        for address in addresses:
            session.delete(address)

        # 2. Удаление корзины пользователя
        cart = session.exec(
            select(Cart).where(Cart.user_id == db_user.id)
        ).first()
        if cart:
            # Удаление элементов корзины
            cart_items = session.exec(
                select(CartItem).where(CartItem.cart_id == cart.id)
            ).all()
            for item in cart_items:
                session.delete(item)
            session.delete(cart)

        # 3. Удаление заказов пользователя
        orders = session.exec(
            select(Order).where(Order.user_id == db_user.id)
        ).all()
        for order in orders:
            # Удаление элементов заказов
            order_items = session.exec(
                select(OrderItem).where(OrderItem.order_id == order.id)
            ).all()
            for item in order_items:
                session.delete(item)
            session.delete(order)

        # Удаляем самого пользователя
        session.delete(db_user)
        session.commit()

        return {
            "status": "success",
            "message": "Аккаунт и все связанные данные успешно удалены",
            "deleted_at": datetime.now(UTC).isoformat()
        }


    # ПРОВЕРКА ДОСТУПА

    @app.get("/auth/verify", tags=["Access Control"])
    async def get_user_role(
            request: Request
    ):

        """Проверка роли текущего пользователя"""

        role = get_role_from_token(request)
        return {"role": role}

    @app.post("/auth/refresh", tags=["Access Control"])
    async def refresh_token(
            request: Request,
            response: Response,
            session: Session = Depends(get_session)
    ):
        refresh_token_cookie = request.cookies.get("refresh_token")
        if not refresh_token_cookie:
            raise HTTPException(status_code=401, detail="Требуется авторизация")

        # Ищем активную сессию
        user_session = session.exec(
            select(UserSession)
            .where(UserSession.refresh_token == refresh_token_cookie)
            .where(UserSession.expires_at > datetime.now(UTC))
        ).first()

        if not user_session:
            raise HTTPException(status_code=401, detail="Недействительный refresh token")

        # Генерируем новый access token
        user = session.get(User, user_session.user_id)
        new_access_token = create_access_token({"sub": user.email, "role": user.role})

        # Обновляем куки (refresh token остается прежним)
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return {"access_token": new_access_token}

