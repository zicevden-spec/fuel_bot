from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.config import get_settings
from app.database.base import async_session
from app.database.models import Report, Station, User
from app.states.admin_states import ModerationReportState, ModerationStationState
from app.keyboards.main import admin_menu_kb

router = Router()
settings = get_settings()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.ADMIN_IDS


@router.message(F.text == "🛡 Модерация")
async def show_moderation_menu(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Отчёты на проверку", callback_data="mod_reports_pending")],
        [InlineKeyboardButton(text="⛽ Заправки на проверку", callback_data="mod_stations_pending")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")],
    ])
    await message.answer("🛡 Меню модерации. Выбери раздел:", reply_markup=kb)


@router.callback_query(F.data == "mod_reports_pending")
async def show_pending_reports(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationReportState.viewing)
    
    async with async_session() as session:
        result = await session.execute(
            select(Report)
            .where(Report.moderation_status == "pending")
            .order_by(Report.created_at.desc())
            .limit(10)
        )
        reports = result.scalars().all()
    
    if not reports:
        await callback.answer("✅ Все отчёты проверены", show_alert=True)
        return
    
    await show_report_card(callback, reports, 0, state)
    await callback.answer()


async def show_report_card(callback: CallbackQuery, reports: list, idx: int, state: FSMContext):
    if idx < 0 or idx >= len(reports):
        return
    
    report = reports[idx]
    
    async with async_session() as session:
        station = await session.get(Station, report.station_id)
        user = await session.get(User, report.user_id)
    
    availability_emoji = {"available": "✅", "low": "⚠️", "unavailable": "❌"}
    queue_emoji = {"none": "🟢", "small": "🟡", "medium": "🟠", "critical": "🔴"}
    availability_text = {"available": "В наличии", "low": "Заканчивается", "unavailable": "Нет"}
    queue_text = {"none": "очереди нет", "small": "маленькая", "medium": "средняя", "critical": "огромная"}
    
    age = datetime.utcnow() - report.created_at
    hours = int(age.total_seconds() // 3600)
    time_str = f"{hours} ч. назад" if hours > 0 else "только что"
    
    price_line = f"💰 Цена: {report.price:.2f}₽\n" if report.price else "💰 Цена: не указана\n"
    
    text = (
        f"📋 Отчёт #{report.id}\n\n"
        f"⛽ {station.name if station else 'Неизвестно'}\n"
        f"📍 {station.address if station else 'Неизвестно'}\n\n"
        f"⛽ Топливо: {report.fuel_type}\n"
        f"{availability_emoji.get(report.availability, '')} Статус: {availability_text.get(report.availability, report.availability)}\n"
        f"{queue_emoji.get(report.queue_level, '')} Очередь: {queue_text.get(report.queue_level, report.queue_level)}\n"
        f"{price_line}"
        f"🕐 Время: {time_str}\n\n"
        f"👤 Пользователь: @{user.username if user and user.username else user.first_name if user else 'Неизвестно'}\n"
        f"🆔 User ID: {report.user_id}"
    )
    
    buttons = []
    if idx > 0:
        buttons.append([InlineKeyboardButton(text="⬅️ Предыдущий", callback_data=f"mod_report_prev:{idx - 1}")])
    if idx < len(reports) - 1:
        buttons.append([InlineKeyboardButton(text="Следующий ➡️", callback_data=f"mod_report_next:{idx + 1}")])
    
    buttons.append([
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"mod_report_approve:{report.id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod_report_reject:{report.id}"),
    ])
    buttons.append([InlineKeyboardButton(text="🔙 В меню модерации", callback_data="mod_reports_pending")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    
    await state.update_data(current_reports=[r.id for r in reports], current_idx=idx)


@router.callback_query(F.data.startswith("mod_report_prev:") | F.data.startswith("mod_report_next:"))
async def navigate_reports(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    reports_ids = data.get("current_reports", [])
    
    if not reports_ids:
        await callback.answer("Ошибка: список отчётов не найден", show_alert=True)
        return
    
    idx = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        result = await session.execute(
            select(Report)
            .where(Report.id.in_(reports_ids))
            .order_by(Report.created_at.desc())
        )
        reports = result.scalars().all()
    
    if reports:
        await show_report_card(callback, list(reports), idx, state)
    
    await callback.answer()


@router.callback_query(F.data.startswith("mod_report_approve:") | F.data.startswith("mod_report_reject:"))
async def moderate_report(callback: CallbackQuery, state: FSMContext):
    action, report_id = callback.data.split(":")
    report_id = int(report_id)
    new_status = "approved" if action == "mod_report_approve" else "rejected"
    
    async with async_session() as session:
        report = await session.get(Report, report_id)
        if report:
            report.moderation_status = new_status
            await session.commit()
    
    data = await state.get_data()
    reports_ids = data.get("current_reports", [])
    current_idx = data.get("current_idx", 0)
    
    async with async_session() as session:
        result = await session.execute(
            select(Report)
            .where(Report.id.in_(reports_ids))
            .order_by(Report.created_at.desc())
        )
        reports = result.scalars().all()
    
    reports_list = list(reports)
    if current_idx >= len(reports_list):
        current_idx = max(0, len(reports_list) - 1)
    
    if reports_list:
        await show_report_card(callback, reports_list, current_idx, state)
    else:
        await callback.message.edit_text("✅ Все отчёты проверены")
    
    await callback.answer(f"Отчёт {'подтверждён' if new_status == 'approved' else 'отклонён'}")


@router.callback_query(F.data == "mod_stations_pending")
async def show_pending_stations(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationStationState.viewing)
    
    async with async_session() as session:
        result = await session.execute(
            select(Station)
            .where(Station.is_verified == False)
            .order_by(Station.created_at.desc())
            .limit(10)
        )
        stations = result.scalars().all()
    
    if not stations:
        await callback.answer("✅ Все заправки проверены", show_alert=True)
        return
    
    await show_station_card(callback, stations, 0, state)
    await callback.answer()


async def show_station_card(callback: CallbackQuery, stations: list, idx: int, state: FSMContext):
    if idx < 0 or idx >= len(stations):
        return
    
    station = stations[idx]
    
    async with async_session() as session:
        city_result = await session.execute(select(func.count()).select_from(Report).where(Report.station_id == station.id))
        reports_count = city_result.scalar()
    
    fuel_types = ", ".join(station.fuel_types) if station.fuel_types else "Не указано"
    
    text = (
        f"⛽ Заправка #{station.id} на проверке\n\n"
        f"🏢 Бренд: {station.brand or 'Не указан'}\n"
        f"📍 Название: {station.name}\n"
        f"🏙 Город ID: {station.city_id}\n"
        f"📍 Адрес: {station.address or 'Не указан'}\n"
        f"⛽ Топливо: {fuel_types}\n"
        f"📊 Отчётов: {reports_count}\n\n"
        f"🕐 Добавлена: {station.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    buttons = []
    if idx > 0:
        buttons.append([InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"mod_station_prev:{idx - 1}")])
    if idx < len(stations) - 1:
        buttons.append([InlineKeyboardButton(text="Следующая ➡️", callback_data=f"mod_station_next:{idx + 1}")])
    
    buttons.append([
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"mod_station_approve:{station.id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod_station_reject:{station.id}"),
    ])
    buttons.append([InlineKeyboardButton(text="🔙 В меню модерации", callback_data="mod_stations_pending")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    
    await state.update_data(current_stations=[s.id for s in stations], current_idx=idx)


@router.callback_query(F.data.startswith("mod_station_prev:") | F.data.startswith("mod_station_next:"))
async def navigate_stations(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    stations_ids = data.get("current_stations", [])
    
    if not stations_ids:
        await callback.answer("Ошибка: список заправок не найден", show_alert=True)
        return
    
    idx = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        result = await session.execute(
            select(Station)
            .where(Station.id.in_(stations_ids))
            .order_by(Station.created_at.desc())
        )
        stations = result.scalars().all()
    
    if stations:
        await show_station_card(callback, list(stations), idx, state)
    
    await callback.answer()


@router.callback_query(F.data.startswith("mod_station_approve:") | F.data.startswith("mod_station_reject:"))
async def moderate_station(callback: CallbackQuery, state: FSMContext):
    action, station_id = callback.data.split(":")
    station_id = int(station_id)
    
    async with async_session() as session:
        station = await session.get(Station, station_id)
        if station:
            if action == "mod_station_approve":
                station.is_verified = True
                station.is_active = True
                msg = "Заправка подтверждена и активирована"
            else:
                station.is_active = False
                msg = "Заправка отклонена и деактивирована"
            await session.commit()
    
    data = await state.get_data()
    stations_ids = data.get("current_stations", [])
    current_idx = data.get("current_idx", 0)
    
    async with async_session() as session:
        result = await session.execute(
            select(Station)
            .where(Station.id.in_(stations_ids))
            .order_by(Station.created_at.desc())
        )
        stations = result.scalars().all()
    
    stations_list = list(stations)
    if current_idx >= len(stations_list):
        current_idx = max(0, len(stations_list) - 1)
    
    if stations_list:
        await show_station_card(callback, stations_list, current_idx, state)
    else:
        await callback.message.edit_text("✅ Все заправки проверены")
    
    await callback.answer(msg)


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_menu(callback: CallbackQuery):
    from app.handlers.user import is_admin as check_admin
    if not check_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    try:
        await callback.message.edit_text("🛠 Админ-панель. Выбери действие:", reply_markup=admin_menu_kb())
    except Exception:
        await callback.message.answer("🛠 Админ-панель. Выбери действие:", reply_markup=admin_menu_kb())
    
    await callback.answer()
