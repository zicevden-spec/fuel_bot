from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def main_menu_kb(is_admin: bool) -> ReplyKeyboardMarkup:
    """Главное меню пользователя"""
    buttons = [
        [KeyboardButton(text="📍 Заправки по городу")],
        [KeyboardButton(text="🎲 Лента заправок")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админка")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def admin_menu_kb() -> ReplyKeyboardMarkup:
    """Меню администратора"""
    buttons = [
        [KeyboardButton(text="➕ Добавить город"), KeyboardButton(text="➕ Добавить заправку")],
        [KeyboardButton(text="📢 Рассылка")],
        [KeyboardButton(text="🔙 Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def back_kb() -> InlineKeyboardMarkup:
    """Кнопка назад для inline-меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
