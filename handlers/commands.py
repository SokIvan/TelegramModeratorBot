from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging
from config import CHANNEL_ID, BAN_LIST_CHAT_ID
from bot import bot

router = Router()
logger = logging.getLogger(__name__)

# ВАШ USER ID
OWNER_ID = 2068329433

def is_owner(user_id: int) -> bool:
    """Проверка, является ли пользователь владельцем"""
    return user_id == OWNER_ID

@router.message(Command("monster_moderator_start"))
async def cmd_start(message: Message):
    """Обработчик команды /monster_moderator_start"""
    logger.info("activated_monster_moderator_start")
    try:
        user = message.from_user
        
        if is_owner(user.id):
            welcome_text = (
                f"👋 <b>Привет, хозяин {user.full_name}!</b>\n\n"
                f"🤖 Я бот-модератор канала.\n\n"
                f"<b>📊 Текущая конфигурация:</b>\n"
                f"📢 Канал: <code>{CHANNEL_ID}</code>\n"

                f"<b>📋 Доступные команды (только для вас):</b>\n"
                f"/monster_moderator_start - это сообщение\n"
                f"/monster_moderator_test - тест отправки в ban-list\n"
                f"/monster_moderator_channel_id - проверить ID текущего чата\n"

                f"✅ Бот работает в локальном режиме!"
            )
        else:
            welcome_text = (
                f"👋 <b>Привет, {user.full_name}!</b>\n\n"
                f"🤖 Я бот-модератор канала.\n"
                f"Извините, но мои команды доступны только владельцу."
            )
        
        await message.reply(welcome_text)
    except Exception as e:
        logger.error(e)


@router.message(Command("monster_moderator_test"))
async def cmd_test_message(message: Message):
    """Тестовая отправка в ban-list чат - /monster_moderator_test"""
    user = message.from_user
    
    if not is_owner(user.id):
        await message.reply("❌ У вас нет прав на использование этой команды.")
        logger.warning(f"User {user.id} tried to use test command without permission")
        return
    
    test_text = (
        f"🧪 <b>ТЕСТОВОЕ СООБЩЕНИЕ</b>\n\n"
        f"👤 <b>Отправитель:</b> {user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"📝 <b>Username:</b> @{user.username if user.username else 'нет'}\n"
        f"💬 <b>Чат:</b> {message.chat.title or 'личные сообщения'} (ID: {message.chat.id})\n\n"
        f"⏰ <b>Время:</b> {message.date}\n\n"
        f"✅ Если вы видите это сообщение в ban-list чате, значит всё работает!"
    )
    
    try:
        sent = await bot.send_message(
            chat_id=BAN_LIST_CHAT_ID,
            text=test_text
        )
        
        await message.reply(
            f"✅ <b>Тестовое сообщение отправлено!</b>\n\n"
            f"📍 Проверьте чат: <code>{BAN_LIST_CHAT_ID}</code>\n"
            f"📎 ID сообщения: <code>{sent.message_id}</code>"
        )

        
    except Exception as e:
        error_text = f"❌ <b>Ошибка отправки:</b>\n<code>{e}</code>"
        await message.reply(error_text)
        logger.error(f"Error sending test message: {e}")

@router.message(Command("monster_moderator_channel_id"))
async def cmd_channel_info(message: Message):
    """Показывает ID текущего чата/канала - /monster_moderator_channel_id"""
    user = message.from_user
    
    if not is_owner(user.id):
        await message.reply("❌ У вас нет прав на использование этой команды.")
        logger.warning(f"User {user.id} tried to use channel_id command without permission")
        return
    
    chat = message.chat
    
    info_text = (
        f"📌 <b>Информация о текущем чате:</b>\n\n"
        f"📋 <b>Название:</b> {chat.title or 'Личный чат'}\n"
        f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
        f"📎 <b>Тип:</b> {chat.type}\n"
        f"👥 <b>Username:</b> @{chat.username if chat.username else 'нет'}\n\n"

    )
    
    await message.reply(info_text)

@router.message(Command("monster_moderator_status"))
async def cmd_status(message: Message):
    """Статус бота - /monster_moderator_status"""
    user = message.from_user
    
    if not is_owner(user.id):
        await message.reply("❌ У вас нет прав на использование этой команды.")
        logger.warning(f"User {user.id} tried to use status command without permission")
        return
    
    # Проверка подключения к Supabase (опционально)
    supabase_status = "✅ Подключено"
    try:
        from database.supabase_db import Database
        await Database.is_trusted(0)
    except Exception as e:
        supabase_status = f"❌ Ошибка: {str(e)[:50]}"
    
    status_text = (
        f"📊 <b>СТАТУС БОТА</b>\n\n"
        f"🤖 <b>Бот:</b> @{bot.username}\n"
        f"⚡ <b>Режим:</b> Локальный (polling)\n"
        f"✅ <b>Статус:</b> Работает\n\n"
        f"<b>🔌 Подключения:</b>\n"
        f"• Telegram API: ✅\n"
        f"• Supabase: {supabase_status}\n\n"
        f"<b>⚙️ Конфигурация:</b>\n"
        f"• Канал: {CHANNEL_ID}\n"
        f"• Ban-list: {BAN_LIST_CHAT_ID}\n"
        f"• Владелец: <code>{OWNER_ID}</code>"
    )
    
    await message.reply(status_text)

# Добавим короткие алиасы для удобства (опционально)
@router.message(Command("mm_start"))
async def cmd_start_short(message: Message):
    """Короткий алиас для /monster_moderator_start"""
    logger.info("activated_mm_start")
    await cmd_start(message)

@router.message(Command("mm_test"))
async def cmd_test_short(message: Message):
    """Короткий алиас для /monster_moderator_test"""
    await cmd_test_message(message)

@router.message(Command("mm_channel_id"))
async def cmd_channel_short(message: Message):
    """Короткий алиас для /monster_moderator_channel_id"""
    await cmd_channel_info(message)

@router.message(Command("mm_status"))
async def cmd_status_short(message: Message):
    """Короткий алиас для /monster_moderator_status"""
    await cmd_status(message)