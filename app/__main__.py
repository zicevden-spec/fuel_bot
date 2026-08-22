import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import get_settings
from app.database.base import init_db
from app.handlers.user import router as user_router
from app.handlers.admin_city import router as admin_city_router
from app.handlers.admin_station import router as admin_station_router
from app.handlers.user_stations import router as user_stations_router
from app.handlers.user_report import router as user_report_router
from app.handlers.user_feed import router as user_feed_router

logger = logging.getLogger(__name__)

async def main():
    settings = get_settings()

    logging.basicConfig(
        level=logging.INFO if settings.DEBUG else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    session = AiohttpSession(proxy=settings.PROXY_URL) if settings.PROXY_URL else None

    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(user_router)
    dp.include_router(admin_city_router)
    dp.include_router(admin_station_router)
    dp.include_router(user_stations_router)
    dp.include_router(user_report_router)
    dp.include_router(user_feed_router)

    logger.info("Бот запускается...")

    await init_db()
    logger.info("База данных готова")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
