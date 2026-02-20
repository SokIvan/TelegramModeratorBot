from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_moderation_keyboard(message_id: int, user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для модерации в Ban-list чате
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Скипнуть",
            callback_data=f"skip:{message_id}:{user_id}"
        ),
        InlineKeyboardButton(
            text="🔨 Забанить",
            callback_data=f"ban:{message_id}:{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👑 Доверенное лицо",
            callback_data=f"trust:{message_id}:{user_id}"
        )
    )
    
    return builder.as_markup()