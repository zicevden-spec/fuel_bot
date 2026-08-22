from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.database.base import async_session
from app.database.models import City, Station
from app.services import station_service as svc

router = Router()


async def safe_edit(message, text, kb):
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass


async def render_cities():
    async with async_session() as session:
        result = await session.execute(select(City).where(City.is_active == True))
        cities = result.scalars().all()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c.name, callback_data=f"city_view:{c.id}")]
        for c in cities
    ])
    return "🏙 Выбери город:", kb, bool(cities)


@router.message(F.text == "📍 Заправки по городу")
async def choose_city(message: Message):
    text, kb, has = await render_cities()
    if not has:
        await message.answer("⚠️ Пока нет доступных городов.")
        return
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "back_cities")
async def back_cities(callback: CallbackQuery):
    text, kb, _ = await render_cities()
    await safe_edit(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data.startswith("city_view:"))
async def choose_brand(callback: CallbackQuery):
    city_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        city = await session.get(City, city_id)

    stations = await svc.get_city_stations(city_id)
    brands = svc.unique_brands(stations)

    if not brands:
        await callback.answer("В этом городе пока нет заправок", show_alert=True)
        return

    kb_rows = []
    for b in brands:
        brand_stations = [s for s in stations if (s.brand or "Другое").strip() == b]
        summaries = [await svc.get_station_summary(s.id) for s in brand_stations]
        merged = svc.merge_summaries(summaries)
        label = f"🏢 {b}" + svc.compact_summary(merged)
        kb_rows.append([InlineKeyboardButton(text=label, callback_data=f"brand_view:{city_id}:{b}")])

    kb_rows.append([InlineKeyboardButton(text="🔙 К городам", callback_data="back_cities")])
    text = f"🏙 {city.name} — выбери бренд:"
    await safe_edit(callback.message, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()


@router.callback_query(F.data.startswith("brand_view:"))
async def choose_address(callback: CallbackQuery):
    _, city_id, brand = callback.data.split(":", 2)
    stations = await svc.get_city_stations(int(city_id))
    brand_stations = [s for s in stations if (s.brand or "Другое").strip() == brand]

    kb_rows = []
    for s in brand_stations:
        summary = await svc.get_station_summary(s.id)
        label = f"📍 {s.address}" + svc.compact_summary(summary)
        kb_rows.append([InlineKeyboardButton(text=label, callback_data=f"station_view:{s.id}")])

    kb_rows.append([InlineKeyboardButton(text="🔙 К брендам", callback_data=f"city_view:{city_id}")])
    text = f"🏢 {brand} — выбери адрес:"
    await safe_edit(callback.message, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()


@router.callback_query(F.data.startswith("station_view:"))
async def show_card(callback: CallbackQuery):
    station_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        station = await session.get(Station, station_id)

    latest = await svc.get_last_reports(station_id)
    card = svc.format_card(station, latest)

    buttons = [
        [InlineKeyboardButton(text=f"📝 Отчёт: {fuel}", callback_data=f"report_fuel:{station_id}:{fuel}")]
        for fuel in (station.fuel_types or [])
    ]
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"station_view:{station_id}"),
        InlineKeyboardButton(text="🔙 К адресам", callback_data=f"brand_view:{station.city_id}:{station.brand}"),
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await safe_edit(callback.message, card, kb)
    await callback.answer()
