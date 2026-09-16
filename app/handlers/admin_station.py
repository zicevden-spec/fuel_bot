from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.config import get_settings
from app.database.base import async_session
from app.database.models import City, Station
from app.services.user_service import get_or_create_user
from app.states.admin_states import AddStation

router = Router()
settings = get_settings()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.ADMIN_IDS


@router.message(F.text == "➕ Добавить заправку")
async def start_add_station(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    async with async_session() as session:
        result = await session.execute(select(City).where(City.is_active == True))
        cities = result.scalars().all()

    if not cities:
        await message.answer("⚠️ Сначала добавь хотя бы один город!")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c.name, callback_data=f"station_city:{c.id}")]
        for c in cities
    ])
    await state.set_state(AddStation.waiting_city)
    await message.answer("🏙 Выбери город для заправки:", reply_markup=kb)


@router.callback_query(AddStation.waiting_city, F.data.startswith("station_city:"))
async def select_city(callback: CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split(":")[1])
    await state.update_data(city_id=city_id)
    await state.set_state(AddStation.waiting_name)
    await callback.message.answer("⛽ Введи название заправки (например: 'Лукойл на Гагарина'):")
    await callback.answer()


@router.message(AddStation.waiting_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddStation.waiting_brand)
    await message.answer("🏢 Введи бренд/сеть (например: Лукойл, Роснефть, Татнефть):")


@router.message(AddStation.waiting_brand)
async def enter_brand(message: Message, state: FSMContext):
    await state.update_data(brand=message.text.strip())
    await state.set_state(AddStation.waiting_address)
    await message.answer("📍 Введи адрес (например: ул. Гагарина, 10):")


@router.message(AddStation.waiting_address)
async def enter_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await state.set_state(AddStation.waiting_fuel)
    await message.answer("⛽ Введи виды топлива через запятую (например: АИ-92, АИ-95, ДТ)")


@router.message(AddStation.waiting_fuel)
async def finish_add_station(message: Message, state: FSMContext):
    data = await state.get_data()
    fuel_types = [f.strip() for f in message.text.split(",") if f.strip()]

    user = await get_or_create_user(message.from_user)

    async with async_session() as session:
        station = Station(
            city_id=data["city_id"],
            name=data["name"],
            brand=data["brand"],
            address=data["address"],
            fuel_types=fuel_types,
            is_verified=True,  # Заправки от админа сразу активны
            created_by=user.id,
        )
        session.add(station)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Заправка '{data['brand']} — {data['name']}' добавлена!")
