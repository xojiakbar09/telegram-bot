import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_VERSION = "1.0.0"
BOT_NAME = "Anime Bot"

# Admin sozlamalari
ADMINS = os.getenv('ADMINS', '').split(',')
DEFAULT_VIP_PRICE = 50000  # So'mda
DEFAULT_CARD_NUMBER = "8600 1234 5678 9012"
DEFAULT_PHONE_NUMBER = "+998901234567"

# Ma'lumotlar bazasi sozlamalari
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///anime_database.db')

# Anime sozlamalari
SUPPORTED_LANGUAGES = ['O\'zbek', 'Rus', 'Turk']
SUPPORTED_COUNTRIES = ['Yaponiya', 'Janubiy Koreya', 'Xitoy']
ANIME_GENRES = [
    'Action', 'Adventure', 'Comedy', 'Drama', 
    'Fantasy', 'Horror', 'Romance', 'Sci-Fi'
]

# Fayl joylashuv sozlamalari
BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / "media"
LOGS_DIR = BASE_DIR / "logs"

# Direktoriyalarni yaratish
MEDIA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Log sozlamalari
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'bot.log',
            'mode': 'a',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True
        },
    },
}

# Bot xabarlari
BOT_MESSAGES = {
    'start': (
        "👋 Assalomu alaykum, {full_name}!\n"
        "Anime botga xush kelibsiz!\n\n"
        "🎬 Bu bot orqali siz:\n"
        "• Anime izlash\n"
        "• Anime ko'rish\n"
        "• VIP bo'lish\n"
        "• Yangi animelar haqida xabar olish\n"
        "imkoniyatlariga ega bo'lasiz!"
    ),
    'help': (
        "🤖 Bot bo'yicha yordam:\n\n"
        "/start - Botni ishga tushirish\n"
        "/search - Anime qidirish\n"
        "/vip - VIP obuna bo'lish\n"
        "/help - Yordam"
    ),
    'not_found': "❌ Anime topilmadi!",
    'error': "❌ Xatolik yuz berdi! Iltimos, qayta urinib ko'ring.",
}

# To'lov tizimlari
PAYMENT_SYSTEMS = {
    'click': {
        'merchant_id': os.getenv('CLICK_MERCHANT_ID'),
        'service_id': os.getenv('CLICK_SERVICE_ID'),
        'secret_key': os.getenv('CLICK_SECRET_KEY'),
    },
    'payme': {
        'merchant_id': os.getenv('PAYME_MERCHANT_ID'),
        'secret_key': os.getenv('PAYME_SECRET_KEY'),
    }
}

# Bot ma'lumotlari
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin_username")

# VIP narxlari
VIP_PRICES = {
    "1_month": 50000,
    "3_months": 120000,
    "6_months": 200000
}

# Reklama narxlari
AD_PRICES = {
    "basic": 50000,    # 24 soat
    "premium": 100000, # 3 kun
    "vip": 200000     # 7 kun
}

# Homiylik narxlari
SPONSOR_PRICES = {
    "silver": 500000,   # oyiga
    "gold": 1000000,    # oyiga
    "platinum": 2000000  # oyiga
}

# Tillar
LANGUAGES = [
    "O'zbek",
    "Rus",
    "Yapon",
    "Korea"
]

# Davlatlar
COUNTRIES = [
    "Yaponiya",
    "Korea",
    "Xitoy",
    "AQSH"
]

# Xabar yuborish sozlamalari
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024
MAX_MEDIA_SIZE = 50 * 1024 * 1024  # 50 MB

# Log fayli
LOG_FILE = LOGS_DIR / "bot.log"

# Bot xabarlari
MESSAGES = {
    "start": (
        "👋 Salom, {full_name}!\n\n"
        "🎬 Anime botga xush kelibsiz!\n"
        "Bu bot orqali siz:\n"
        "• Anime qidirishingiz\n"
        "• Ma'lumotlarni ko'rishingiz\n"
        "• Epizodlarni yuklab olishingiz mumkin!\n\n"
        "Boshlash uchun quyidagi tugmalardan birini tanlang:"
    ),
    "help": (
        "ℹ️ BOT YORDAM\n\n"
        "Bot buyruqlari:\n"
        "/start - Botni ishga tushirish\n"
        "/search - Anime qidirish\n"
        "/help - Yordam\n\n"
        "Qo'shimcha funksiyalar:\n"
        "• Anime nomi orqali qidirish\n"
        "• Anime kodi orqali qidirish\n"
        "• Janr bo'yicha qidirish\n"
        "• Tasodifiy anime\n"
        "• VIP obuna\n\n"
        "Muammo yuzaga kelsa, @{admin_username} ga murojaat qiling."
    ),
    "not_found": "❌ Anime topilmadi!",
    "vip_required": "👑 Bu funksiyadan foydalanish uchun VIP bo'lishingiz kerak!",
    "admin_only": "❌ Bu funksiya faqat adminlar uchun!",
    "error": "❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
} 