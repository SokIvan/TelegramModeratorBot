import asyncio
import logging
from bot import bot, dp
import handlers.channel
import handlers.commands
from database.supabase_db import Database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def on_startup():
    """Действия при запуске"""
    logger.info("=" * 50)
    logger.info("🚀 Бот запускается...")
    logger.info("📋 Проверка подключения к Supabase...")
    
    try:
        test_user = await Database.is_trusted(0)
        logger.info("✅ Подключение к Supabase успешно!")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Supabase: {e}")
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    logger.info("⏩ Пропускаем старые апдейты...")
    logger.info("✅ Бот готов к работе!")
    logger.info("=" * 50)

async def on_shutdown():
    """Действия при остановке"""
    logger.info("🛑 Бот останавливается...")
    await bot.session.close()
    logger.info("✅ Бот остановлен")

async def main():
    """Главная функция"""
    await on_startup()
    
    try:
        # Запускаем поллинг с пропуском старых апдейтов
        await dp.start_polling(
            bot,
            skip_updates=True  # ВОТ ЭТО РЕШЕНИЕ!
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при работе бота: {e}")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())