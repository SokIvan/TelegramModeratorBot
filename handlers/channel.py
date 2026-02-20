from aiogram import F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, MEMBER
from bot import dp
from database.supabase_db import Database
from utils.detector import BotDetector
from keyboards.inline import get_moderation_keyboard
from config import CHANNEL_ID, BAN_LIST_CHAT_ID
import logging

detector = BotDetector()

@dp.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER))
async def on_user_join(event, bot: Bot):
    """Отслеживание новых участников (опционально)"""
    # Здесь можно добавить логику для новых участников
    pass

@dp.message(F.chat.id == CHANNEL_ID)
async def channel_message_handler(message: Message, bot: Bot):
    """
    Обработчик всех сообщений в канале
    """
    try:
        # Проверяем, не является ли автор доверенным
        if await Database.is_trusted(message.from_user.id):
            return
        
        # Проверяем сообщение на подозрительность
        user_info = {
            "id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        
        if await detector.is_suspicious(message.text or message.caption or "", user_info):
            # Отправляем в Ban-list чат на модерацию
            await send_to_moderation(message, bot)
            
    except Exception as e:
        logging.error(f"Error in channel_message_handler: {e}")

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