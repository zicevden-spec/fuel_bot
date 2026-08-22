from sqlalchemy import select
from aiogram.types import User as TgUser
from app.database.base import async_session
from app.database.models import User


async def get_or_create_user(tg_user: TgUser) -> User:
    """Получает пользователя из БД или создаёт нового"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            await session.commit()

        return user
