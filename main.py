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

# Флаг для отслеживания состояния polling
polling_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global polling_task
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
    logger.info("⏩ Запускаем polling...")
    
    polling_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))
    logger.info("✅ Бот готов к работе!")
    
    # Запускаем периодический пинг
    if RENDER_EXTERNAL_URL:
        asyncio.create_task(periodic_ping())
        logger.info(f"🔄 Самопинг запущен для {RENDER_EXTERNAL_URL}")
    
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    logger.info("🛑 Бот останавливается...")
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error stopping polling: {e}")
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
    """Webhook endpoint (на случай если переключимся с polling)"""
    try:
        update = await request.json()
        await dp.feed_update(bot, Update(**update))
        return {"ok": True}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
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
                        logger.info(f"Ping successful at {RENDER_EXTERNAL_URL}")
                    else:
                        logger.warning(f"Ping failed with status {resp.status}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Ping error: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        log_level="info"
    )