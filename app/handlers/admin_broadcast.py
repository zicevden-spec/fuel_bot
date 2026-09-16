from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func

from app.config import get_settings
from app.database.base import async_session
from app.database.models import User, Broadcast, BroadcastLog
from app.states.admin_states import BroadcastState
from app.keyboards.main import admin_menu_kb

router = Router()
settings = get_settings()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.ADMIN_IDS


@router.message(F.text == "📢 Рассылка")
async def start_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    
    await state.set_state(BroadcastState.waiting_message)
    await message.answer(
        "📢 Создание рассылки\n\n"
        "Введите текст сообщения для всех пользователей бота.\n\n"
        "Используйте /cancel для отмены."
    )


@router.message(BroadcastState.waiting_message, F.text != "/cancel")
async def receive_broadcast_message(message: Message, state: FSMContext):
    text = message.text.strip()
    
    if len(text) < 5:
        await message.answer("❌ Сообщение слишком короткое. Введите более подробный текст.")
        return
    
    await state.update_data(message_text=text)
    await state.set_state(BroadcastState.confirming)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ])
    
    preview = (
        f"📢 Предпросмотр рассылки:\n\n"
        f"{text}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"Нажмите 'Отправить' для подтверждения."
    )
    
    await message.answer(preview, reply_markup=kb)


@router.callback_query(BroadcastState.confirming, F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    from app.services.user_service import get_or_create_user
    
    data = await state.get_data()
    message_text = data.get("message_text")
    
    if not message_text:
        await callback.answer("Ошибка: текст сообщения не найден", show_alert=True)
        await state.clear()
        return
    
    admin_user = await get_or_create_user(callback.from_user)
    
    async with async_session() as session:
        broadcast = Broadcast(
            admin_id=admin_user.id,
            message_text=message_text,
            status="pending"
        )
        session.add(broadcast)
        await session.commit()
        await session.refresh(broadcast)
        
        result = await session.execute(
            select(func.count()).select_from(User).where(User.is_blocked == False)
        )
        total_users = result.scalar() or 0
        broadcast.recipients_count = total_users
        broadcast.status = "in_progress"
        await session.commit()
    
    await callback.message.edit_text(
        f"📢 Рассылка запущена!\n\n"
        f"Получателей: {total_users}\n"
        f"Статус: в процессе..."
    )
    
    await send_broadcast(callback.bot, broadcast.id, message_text)
    await state.clear()


@router.callback_query(BroadcastState.confirming, F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена.", reply_markup=admin_menu_kb())
    await callback.answer("Рассылка отменена")


@router.message(BroadcastState.waiting_message, F.text == "/cancel")
@router.message(BroadcastState.confirming, F.text == "/cancel")
async def cancel_broadcast_message(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Рассылка отменена.", reply_markup=admin_menu_kb())


async def send_broadcast(bot, broadcast_id: int, message_text: str):
    """Фоновая отправка рассылки всем пользователям"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.is_blocked == False)
        )
        users = result.scalars().all()
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message_text,
                    parse_mode="HTML"
                )
                log = BroadcastLog(
                    broadcast_id=broadcast_id,
                    user_id=user.id,
                    status="sent"
                )
                session.add(log)
                sent += 1
            except Exception as e:
                log = BroadcastLog(
                    broadcast_id=broadcast_id,
                    user_id=user.id,
                    status="failed",
                    error_message=str(e)
                )
                session.add(log)
                failed += 1
            
            if sent % 10 == 0:
                await session.commit()
        
        broadcast = await session.get(Broadcast, broadcast_id)
        if broadcast:
            broadcast.sent_count = sent
            broadcast.failed_count = failed
            broadcast.status = "completed"
            broadcast.finished_at = func.now()
        
        await session.commit()
