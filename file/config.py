import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8245541977:AAGhAZHg0GOLZtneG040-_TZfuNktCte4rI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6810310065"))
DATABASE_PATH = "giveaway_bot.db"