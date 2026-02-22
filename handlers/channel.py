from aiogram import F, Bot
from aiogram.types import Message, CallbackQuery, ReactionTypeEmoji
from bot import dp, bot
from database.supabase_db import Database
from utils.detector import BotDetector
from keyboards.inline import get_moderation_keyboard
from config import CHANNEL_ID, BAN_LIST_CHAT_ID
from handlers.commands import router as commands_router
import logging

logger = logging.getLogger(__name__)
detector = BotDetector()

# Подключаем роутер с командами
dp.include_router(commands_router)

# ID владельца
OWNER_ID = 2068329433



@dp.message()
async def channel_message_handler(message: Message):
    """Обработка всех сообщений, которые видит бот"""

    if message.sender_chat:
        return
    
    if not message.from_user:
        return
    
    await handle_user_message(message)

async def handle_user_message(message: Message):
    """Обработка сообщений от пользователей в канале"""
    try:
        
        # Проверка на доверенное лицо
        is_trusted = await Database.is_trusted(message.from_user.id)

        
        if is_trusted:
            return
        
        # Подготовка данных для детектора
        user_info = {
            "id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        
        text_to_check = message.text or message.caption or ""
        
        # Запуск детектора

        is_susp = await detector.is_suspicious(text_to_check, user_info)

        
        if is_susp:

            
            # Ставим реакцию
            try:
                await message.react([ReactionTypeEmoji(emoji="👀")])

            except Exception as e:
                logger.error(f"❌ Не удалось поставить реакцию: {e}")
            
            # Отправляем в бан-лист
            await send_to_moderation(message)

        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_user_message: {e}", exc_info=True)


async def send_to_moderation(message: Message):
    """Отправка в бан-лист группу"""
    from bot import bot
    
    user = message.from_user
    message_text = message.text or message.caption or "[Медиафайл]"
    

    
    # Ссылка на сообщение
    if message.chat.username:
        message_link = f"https://t.me/{message.chat.username}/{message.message_id}"
    else:
        message_link = f"Сообщение ID: {message.message_id}"
    
    text = (
        f"👾 <b>ПОДОЗРИТЕЛЬНЫЙ ПОЛЬЗОВАТЕЛЬ</b>\n\n"
        f"👤 <b>Имя:</b> {user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"📝 <b>Username:</b> @{user.username if user.username else 'нет'}\n"
        f"🔗 <b>Ссылка:</b> {message_link}\n"
        f"💬 <b>Сообщение:</b>\n{message_text}\n\n"
        f"👀 <b>Что делать?</b>"
    )
    
    try:
        sent = await bot.send_message(
            chat_id=BAN_LIST_CHAT_ID,
            text=text,
            reply_markup=get_moderation_keyboard(message.message_id, user.id)
        )

        
        # Сохраняем в БД
        await Database.add_to_ban_list(
            chat_id=message.chat.id,
            message_id=message.message_id,
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            suspect_message=message_text
        )

        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в бан-лист: {e}")

# Обработка кнопок модерации
@dp.callback_query(lambda c: c.data.startswith(('skip:', 'ban:', 'trust:')))
async def moderation_callback(callback: CallbackQuery):
    """Обработка нажатий на кнопки"""
    from bot import bot
    
    action, message_id, user_id = callback.data.split(':')
    message_id = int(message_id)
    user_id = int(user_id)
    
    moderator = callback.from_user

    
    try:
        if action == 'skip':
            await Database.update_suspect_status(message_id, 'skipped')
            await callback.message.edit_text(
                callback.message.text + f"\n\n✅ <b>Пропущено модератором @{moderator.username}</b>"
            )
            await callback.answer("✅ Пропущено")
            
        elif action == 'ban':
            try:
                await bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

                
                await Database.update_suspect_status(message_id, 'banned')
                
                try:
                    await bot.delete_message(chat_id=CHANNEL_ID, message_id=message_id)

                except Exception as e:
                    logger.error(f"❌ Не удалось удалить сообщение: {e}")
                
                await callback.message.edit_text(
                    callback.message.text + f"\n\n🔨 <b>Забанен модератором @{moderator.username}</b>"
                )
                await callback.answer("🔨 Забанен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка бана: {e}")
                await callback.answer(f"Ошибка: {e}", show_alert=True)
                
        elif action == 'trust':
            await Database.add_trusted_user(
                user_id=user_id,
                username=moderator.username,
                full_name=moderator.full_name
            )
            await Database.update_suspect_status(message_id, 'trusted')
            await callback.message.edit_text(
                callback.message.text + f"\n\n👑 <b>Доверенный (добавил @{moderator.username})</b>"
            )
            await callback.answer("👑 Добавлен в доверенные")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в moderation_callback: {e}", exc_info=True)
        await callback.answer("Ошибка", show_alert=True)