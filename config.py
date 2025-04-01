import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = os.getenv("ADMINS").split(",")
DB_URL = os.getenv("DB_URL") 