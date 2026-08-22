from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.database.base import async_session
from app.database.models import City, Station
from app.services import station_service as svc

router = Router()


async def render_feed_cities():
    async with async_session() as session:
        result = await session.execute(select(City).where(City.is_active == True))
        cities = result.scalars().all()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c.name, callback_data=f"feed_city:{c.id}")]
        for c in cities
    ])
    return "🏙 Выбери город для ленты:", kb, bool(cities)


async def get_city_stations(city_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Station).where(
                Station.city_id == city_id,
                Station.is_active == True,
                Station.is_verified == True,
            )
        )
        return result.scalars().all()


@router.message(F.text == "🎲 Лента заправок")
async def start_feed(message: Message):
    text, kb, has = await render_feed_cities()
    if not has:
        await message.answer("⚠️ Пока нет доступных городов.")
        return
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "feed_cities_back")
async def feed_cities_back(callback: CallbackQuery):
    text, kb, _ = await render_feed_cities()
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("feed_city:"))
async def feed_city(callback: CallbackQuery):
    city_id = int(callback.data.split(":")[1])
    await show_feed(callback, city_id, 0)
    await callback.answer()


@router.callback_query(F.data.startswith("feed_next:"))
async def next_feed(callback: CallbackQuery):
    _, city_id, offset = callback.data.split(":")
    await show_feed(callback, int(city_id), int(offset))
    await callback.answer()


async def show_feed(callback: CallbackQuery, city_id: int, offset: int):
    stations = await get_city_stations(city_id)

    if not stations:
        await callback.message.answer("⚠️ В этом городе пока нет заправок.")
        return

    idx = offset % len(stations)
    station = stations[idx]

    latest = await svc.get_last_reports(station.id)
    card = svc.format_feed_card(station, latest)
    card += f"\n\n🎲 {idx + 1}/{len(stations)}"

    buttons = [
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"feed_next:{city_id}:{idx - 1}"),
            InlineKeyboardButton(text="➡️ Дальше", callback_data=f"feed_next:{city_id}:{idx + 1}"),
        ],
        [InlineKeyboardButton(text="🔙 К городам", callback_data="feed_cities_back")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.edit_text(card, reply_markup=kb)
    except TelegramBadRequest:
        pass
