from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from app.config import get_settings
from app.services.user_service import get_or_create_user

router = Router()
settings = get_settings()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await get_or_create_user(message.from_user)

    if message.from_user.id in settings.ADMIN_IDS:
        role_text = "👑 Ты администратор"
    else:
        role_text = "👤 Ты обычный пользователь"

    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот для отслеживания состояния АЗС.\n"
        f"{role_text}"
    )
