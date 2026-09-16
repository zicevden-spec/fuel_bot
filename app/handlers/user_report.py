from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message

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

PRICE_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⏭ Пропустить", callback_data="rep_price_skip")],
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
async def choose_queue(callback: CallbackQuery, state: FSMContext):
    queue_level = callback.data.split(":")[1]
    await state.update_data(queue_level=queue_level)
    await state.set_state(ReportState.waiting_price)
    await callback.message.edit_text(
        "💰 Какая цена за литр? (введи число, например: 58.50)\nИли нажми 'Пропустить'", reply_markup=PRICE_KB
    )
    await callback.answer()


@router.message(ReportState.waiting_price)
async def enter_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
        await state.update_data(price=price)
        await finish_report(message, state, from_text=True)
    except ValueError:
        await message.answer("❌ Введи корректное число, например: 58.50")


@router.callback_query(ReportState.waiting_price, F.data == "rep_price_skip")
async def skip_price(callback: CallbackQuery, state: FSMContext):
    await state.update_data(price=None)
    await finish_report(callback, state, from_text=False)
    await callback.answer()


async def finish_report(event, state: FSMContext, from_text: bool):
    data = await state.get_data()
    await state.clear()

    if from_text:
        user = await get_or_create_user(event.from_user)
        message = event
    else:
        user = await get_or_create_user(event.from_user)
        message = event.message

    async with async_session() as session:
        report = Report(
            station_id=data["station_id"],
            user_id=user.id,
            fuel_type=data["fuel"],
            availability=data["availability"],
            queue_level=data["queue_level"],
            price=data.get("price"),
            moderation_status="approved"  # Отчёт публикуется сразу без модерации
        )
        session.add(report)
        await session.commit()

    await message.answer("✅ Спасибо! Твой отчёт опубликован.")
