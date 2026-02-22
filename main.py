from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import logging
from aiogram.types import Update
import aiohttp

from bot import bot, dp
from config import RENDER_EXTERNAL_URL
import handlers.channel
import handlers.commands
from database.supabase_db import Database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 50)
    logger.info("🚀 Бот запускается...")
    logger.info("📋 Проверка подключения к Supabase...")
    
    try:
        test_user = await Database.is_trusted(0)
        logger.info("✅ Подключение к Supabase успешно!")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Supabase: {e}")
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    
    # Устанавливаем вебхук
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        try:
            await bot.set_webhook(
                webhook_url,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True
            )
            logger.info(f"✅ Вебхук установлен на {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Ошибка установки вебхука: {e}")
    else:
        logger.warning("⚠️ RENDER_EXTERNAL_URL не указан, вебхук не установлен")
    
    # Запускаем периодический пинг
    if RENDER_EXTERNAL_URL:
        asyncio.create_task(periodic_ping())
        logger.info(f"🔄 Самопинг запущен для {RENDER_EXTERNAL_URL}")
    
    logger.info("✅ Бот готов к работе!")
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    logger.info("🛑 Бот останавливается...")
    
    # Удаляем вебхук
    try:
        await bot.delete_webhook()
        logger.info("✅ Вебхук удалён")
    except Exception as e:
        logger.error(f"❌ Ошибка удаления вебхука: {e}")
    
    await bot.session.close()
    logger.info("✅ Бот остановлен")

# Создаем FastAPI приложение
app = FastAPI(
    title="MonsterGifts Bot",
    description="Bot for monitoring channel messages",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "status": "alive", 
        "message": "MonsterGifts Bot is running",
        "python_version": "3.11"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/webhook")
async def webhook(request: Request):
    """Webhook endpoint для приема обновлений от Telegram"""
    try:
        update_data = await request.json()
        update = Update(**update_data)
        
        # Передаем обновление диспетчеру
        await dp.feed_update(bot, update)
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}

async def periodic_ping():
    """Пинг каждые 10 минут, чтобы Render не засыпал"""
    if not RENDER_EXTERNAL_URL:
        logger.warning("RENDER_EXTERNAL_URL not set, skipping ping")
        return
        
    while True:
        await asyncio.sleep(600)  # 10 минут
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{RENDER_EXTERNAL_URL}/health") as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Пинг успешен: {RENDER_EXTERNAL_URL}")
                    else:
                        logger.warning(f"⚠️ Пинг вернул статус {resp.status}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка пинга: {e}")

if __name__ == "__main__":
    # Для локального тестирования можно использовать polling
    # Но на Render используем uvicorn через команду в Dockerfile/start command
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        log_level="info"
    )