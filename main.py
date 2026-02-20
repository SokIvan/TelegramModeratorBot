from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import logging
from aiogram.types import Update
import aiohttp

from bot import bot, dp
from config import RENDER_EXTERNAL_URL
import handlers  # импортируем все хендлеры

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Флаг для отслеживания состояния polling
polling_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global polling_task
    logging.info("Starting bot polling...")
    polling_task = asyncio.create_task(dp.start_polling(bot))
    
    # Запускаем периодический пинг
    asyncio.create_task(periodic_ping())
    
    yield
    
    # Shutdown
    logging.info("Stopping bot polling...")
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

# Создаем FastAPI приложение
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "alive", "message": "MonsterGifts Bot is running"}

@app.post("/webhook")
async def webhook(request: Request):
    """Webhook endpoint (на случай если переключимся с polling)"""
    update = await request.json()
    await dp.feed_update(bot, Update(**update))
    return {"ok": True}

async def periodic_ping():
    """Пинг каждые 10 минут, чтобы Render не засыпал"""
    if not RENDER_EXTERNAL_URL:
        logging.warning("RENDER_EXTERNAL_URL not set, skipping ping")
        return
        
    while True:
        await asyncio.sleep(600)  # 10 минут
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(RENDER_EXTERNAL_URL) as resp:
                    if resp.status == 200:
                        logging.info("Ping successful")
                    else:
                        logging.warning(f"Ping failed with status {resp.status}")
        except Exception as e:
            logging.error(f"Ping error: {e}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)