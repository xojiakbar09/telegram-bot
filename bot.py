import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from handlers import user_handlers, admin_handlers
from database import init_models, check_admin_data
from settings import (
    BOT_TOKEN, 
    LOGGING_CONFIG, 
    BOT_VERSION,
    BOT_NAME
)
import logging.config

# Loglarni sozlash
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Bot va Dispatcher yaratish
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Handlerlarni ro'yxatdan o'tkazish
dp.include_router(admin_handlers.router)
dp.include_router(user_handlers.router)

# Botni ishga tushirish
async def main():
    logger.info(f"Bot ishga tushirilmoqda... ({BOT_NAME} v{BOT_VERSION})")
    
    # Ma'lumotlar bazasini yaratish
    try:
        await init_models()
        logger.info("Ma'lumotlar bazasi muvaffaqiyatli yaratildi")
    except Exception as e:
        logger.error(f"Ma'lumotlar bazasini yaratishda xatolik: {e}")
        return
    
    try:
        # Admin ma'lumotlarini tekshirish
        await check_admin_data()
        
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Botni ishga tushirishda xatolik: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi!")
