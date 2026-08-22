from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# Создаём асинхронный движок для подключения к БД
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Фабрика сессий для работы с БД
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


async def init_db():
    """Создаёт все таблицы в базе данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
