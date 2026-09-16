from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from app.config import get_settings
from app.keyboards.main import main_menu_kb
from app.services.user_service import get_or_create_user

router = Router()
settings = get_settings()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.ADMIN_IDS


@router.message(CommandStart())
async def cmd_start(message: Message):
    await get_or_create_user(message.from_user)
    admin = is_admin(message.from_user.id)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот для отслеживания состояния АЗС.",
        reply_markup=main_menu_kb(admin)
    )


@router.message(F.text == "🔙 Назад")
async def back_to_main(message: Message):
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_kb(is_admin(message.from_user.id))
    )
