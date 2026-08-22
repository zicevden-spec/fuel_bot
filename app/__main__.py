import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import get_settings
from app.handlers.user import router as user_router

logger = logging.getLogger(__name__)

async def main():
    settings = get_settings()
    
    logging.basicConfig(
        level=logging.INFO if settings.DEBUG else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создаём сессию с прокси, если он указан
    session = AiohttpSession(proxy=settings.PROXY_URL) if settings.PROXY_URL else None
    
    # Создаём бота с настройками по умолчанию
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    dp.include_router(user_router)
    
    logger.info("Бот запускается...")
    if settings.PROXY_URL:
        logger.info(f"Используется прокси: {settings.PROXY_URL}")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
