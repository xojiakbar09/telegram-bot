from dotenv import load_dotenv
import os

# .env faylini yuklash
load_dotenv()

# O'zgaruvchilarni tekshirish
print("BOT_TOKEN:8045600076:AAF46_KDklJ2aejvsuKhqqx_lGCfBlsr8LQ", os.getenv("8045600076:AAF46_KDklJ2aejvsuKhqqx_lGCfBlsr8LQ"))
print("ADMINS:8074021131", os.getenv("8074021131"))
print("DB_URL:sqlite+aiosqlite:///database.db", os.getenv("sqlite+aiosqlite:///database.db"))
