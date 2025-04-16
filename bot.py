import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from handlers import user_handlers, admin_handlers
from database import create_tables, check_admin_data
import os
from dotenv import load_dotenv

# .env faylidan BOT_TOKEN ni o'qish
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/bot.log'
)

# Bot va Dispatcher yaratish
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Handlerlarni ro'yxatdan o'tkazish
dp.include_router(admin_handlers.router)
dp.include_router(user_handlers.router)

# Asosiy funksiya
async def main():
    logging.info("Bot ishga tushirilmoqda...")
    
    # Ma'lumotlar bazasi jadvallarini yaratish
    await create_tables()
    
    # Admin ma'lumotlarini tekshirish
    await check_admin_data()
    
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot to'xtatildi")
    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
