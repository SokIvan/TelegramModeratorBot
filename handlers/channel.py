from aiogram import F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, MEMBER
from bot import dp, bot
from database.supabase_db import Database
from utils.detector import BotDetector
from keyboards.inline import get_moderation_keyboard
from config import CHANNEL_ID, BAN_LIST_CHAT_ID
import logging

logger = logging.getLogger(__name__)
detector = BotDetector()

# Определяем тип идентификатора канала
try:
    CHANNEL_ID_INT = int(CHANNEL_ID)  # если это число
except ValueError:
    CHANNEL_ID_INT = None
    CHANNEL_USERNAME = CHANNEL_ID.lstrip('@') if CHANNEL_ID.startswith('@') else CHANNEL_ID

@dp.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER))
async def on_user_join(event, bot: Bot):
    pass

# Фильтр сообщений из канала
if CHANNEL_ID_INT is not None:
    @dp.message(F.chat.id == CHANNEL_ID_INT)
    async def channel_message_handler(message: Message):
        await handle_channel_message(message)
else:
    @dp.message(F.chat.username == CHANNEL_USERNAME)
    async def channel_message_handler(message: Message):
        await handle_channel_message(message)

async def handle_channel_message(message: Message):
    try:
        logger.info(f"Received message in channel from user {message.from_user.id}: {message.text or message.caption or '[no text]'}")
        
        # Проверка на доверенное лицо
        if await Database.is_trusted(message.from_user.id):
            logger.info(f"User {message.from_user.id} is trusted, skipping")
            return
        
        user_info = {
            "id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        
        text_to_check = message.text or message.caption or ""
        is_susp = await detector.is_suspicious(text_to_check, user_info)
        logger.info(f"Suspicious check result: {is_susp} for message: {text_to_check[:50]}")
        
        if is_susp:
            logger.info(f"Suspicious message detected, sending to moderation chat")
            await send_to_moderation(message)
        else:
            logger.debug("Message not suspicious")
            
    except Exception as e:
        logger.error(f"Error in handle_channel_message: {e}", exc_info=True)


async def send_to_moderation(message: Message, bot: Bot):
    """
    Отправляет сообщение в чат модерации
    """
    user = message.from_user
    message_text = message.text or message.caption or "[Медиафайл]"
    
    # Формируем текст для модератора
    text = (
        f"👾 <b>ПОДОЗРИТЕЛЬНЫЙ ПОЛЬЗОВАТЕЛЬ</b>\n\n"
        f"👤 <b>Имя:</b> {user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"📝 <b>Username:</b> @{user.username if user.username else 'нет'}\n"
        f"💬 <b>Сообщение:</b>\n{message_text}\n\n"
        f"👀 <b>Что делать?</b>"
    )
    
    # Отправляем в Ban-list чат
    sent_message = await bot.send_message(
        chat_id=BAN_LIST_CHAT_ID,
        text=text,
        reply_markup=get_moderation_keyboard(message.message_id, user.id)
    )
    logger.info(f"Sending message {message.message_id} from user {message.from_user.id} to ban-list")
    # Сохраняем в базу
    await Database.add_to_ban_list(
        chat_id=message.chat.id,
        message_id=message.message_id,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        suspect_message=message_text
    )

@dp.callback_query(lambda c: c.data.startswith(('skip:', 'ban:', 'trust:')))
async def moderation_callback(callback: CallbackQuery, bot: Bot):
    """
    Обработка нажатий на кнопки модерации
    """
    action, message_id, user_id = callback.data.split(':')
    message_id = int(message_id)
    user_id = int(user_id)
    
    try:
        if action == 'skip':
            # Просто помечаем как пропущенного
            await Database.update_suspect_status(message_id, 'skipped')
            await callback.message.edit_text(
                callback.message.text + "\n\n✅ <b>Пользователь пропущен</b>"
            )
            
        elif action == 'ban':
            # Баним пользователя
            try:
                # Удаляем все сообщения пользователя в канале
                # (это сложно сделать напрямую, но можно банить и удалять последнее)
                await bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                await Database.update_suspect_status(message_id, 'banned')
                
                # Пытаемся удалить сообщение из канала
                try:
                    await bot.delete_message(chat_id=CHANNEL_ID, message_id=message_id)
                except:
                    pass
                
                await callback.message.edit_text(
                    callback.message.text + "\n\n🔨 <b>Пользователь был съеден монстром!</b> 🐉"
                )
            except Exception as e:
                await callback.answer(f"Ошибка бана: {e}", show_alert=True)
                
        elif action == 'trust':
            # Добавляем в доверенные
            user = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            await Database.add_trusted_user(
                user_id=user_id,
                username=user.user.username,
                full_name=user.user.full_name
            )
            await Database.update_suspect_status(message_id, 'trusted')
            await callback.message.edit_text(
                callback.message.text + "\n\n👑 <b>Пользователь теперь доверенное лицо!</b>"
            )
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in moderation_callback: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)