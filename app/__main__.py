import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import get_settings

logger = logging.getLogger(__name__)

async def main():
    settings = get_settings()
    
    logging.basicConfig(
        level=logging.INFO if settings.DEBUG else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
    dp = Dispatcher()
    
    logger.info("Бот запускается...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
