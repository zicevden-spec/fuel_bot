from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.database.base import async_session
from app.database.models import Report
from app.services.user_service import get_or_create_user
from app.states.user_states import ReportState

router = Router()

AVAILABILITY_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ В наличии", callback_data="rep_avail:available")],
    [InlineKeyboardButton(text="⚠️ Заканчивается", callback_data="rep_avail:low")],
    [InlineKeyboardButton(text="❌ Нет", callback_data="rep_avail:unavailable")],
])

QUEUE_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟢 Очереди нет", callback_data="rep_queue:none")],
    [InlineKeyboardButton(text="🟡 Маленькая", callback_data="rep_queue:small")],
    [InlineKeyboardButton(text="🟠 Средняя", callback_data="rep_queue:medium")],
    [InlineKeyboardButton(text="🔴 Огромная", callback_data="rep_queue:critical")],
])


@router.callback_query(F.data.startswith("report_fuel:"))
async def start_report(callback: CallbackQuery, state: FSMContext):
    _, station_id, fuel = callback.data.split(":", 2)
    await state.set_state(ReportState.waiting_availability)
    await state.update_data(station_id=int(station_id), fuel=fuel)
    await callback.message.edit_text(
        f"⛽ {fuel}\n\nЕсть ли это топливо на заправке?", reply_markup=AVAILABILITY_KB
    )
    await callback.answer()


@router.callback_query(ReportState.waiting_availability, F.data.startswith("rep_avail:"))
async def choose_availability(callback: CallbackQuery, state: FSMContext):
    availability = callback.data.split(":")[1]
    await state.update_data(availability=availability)
    await state.set_state(ReportState.waiting_queue)
    await callback.message.edit_text("🚗 Какая очередь на заправке?", reply_markup=QUEUE_KB)
    await callback.answer()


@router.callback_query(ReportState.waiting_queue, F.data.startswith("rep_queue:"))
async def finish_report(callback: CallbackQuery, state: FSMContext):
    queue_level = callback.data.split(":")[1]
    data = await state.get_data()
    await state.clear()

    user = await get_or_create_user(callback.from_user)

    async with async_session() as session:
        report = Report(
            station_id=data["station_id"],
            user_id=user.id,
            fuel_type=data["fuel"],
            availability=data["availability"],
            queue_level=queue_level,
        )
        session.add(report)
        await session.commit()

    await callback.message.answer("✅ Спасибо! Твой отчёт сохранён.")
    await callback.answer()
