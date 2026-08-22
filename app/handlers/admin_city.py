from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.config import get_settings
from app.database.base import async_session
from app.database.models import City
from app.keyboards.main import admin_menu_kb
from app.states.admin_states import AddCity

router = Router()
settings = get_settings()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.ADMIN_IDS


@router.message(F.text == "⚙️ Админка")
async def show_admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    await message.answer("🛠 Админ-панель. Выбери действие:", reply_markup=admin_menu_kb())


@router.message(F.text == "➕ Добавить город")
async def start_add_city(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddCity.waiting_name)
    await message.answer("🏙 Введи название города для добавления:")


@router.message(AddCity.waiting_name)
async def finish_add_city(message: Message, state: FSMContext):
    city_name = message.text.strip()

    async with async_session() as session:
        existing = await session.execute(select(City).where(City.name.ilike(city_name)))
        if existing.scalar_one_or_none():
            await message.answer(f"⚠️ Город '{city_name}' уже существует")
        else:
            session.add(City(name=city_name))
            await session.commit()
            await message.answer(f"✅ Город '{city_name}' добавлен!", reply_markup=admin_menu_kb())

    await state.clear()
