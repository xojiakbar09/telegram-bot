from telegram import Update
from telegram.ext import Application, CommandHandler
import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()
TOKEN = os.getenv("TOKEN")  # .env faylidan TOKEN ni olish

if not TOKEN:
    raise ValueError("TOKEN topilmadi! Iltimos, .env fayliga TOKEN ni qo'shing.")

# Botni ishga tushirish
app = Application.builder().token(TOKEN).build()

# /start buyrug‘ini qo‘shish
async def start(update: Update, context):
    await update.message.reply_text("Salom! Bu botda o‘zbek tiliga dublaj qilingan animelar chiqadi!")

app.add_handler(CommandHandler("start", start))

# Botni ishga tushirish
print("Bot ishga tushdi...")
app.run_polling()
