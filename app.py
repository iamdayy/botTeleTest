import os
from dotenv import load_dotenv

import telebot

from database import Database
from handlers import WorkReportHandlers

load_dotenv()  # Memuat variabel lingkungan dari file .env

def main():
    # Pakai environment variable agar token tidak wajib ditulis langsung di kode.
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot = telebot.TeleBot(token)
    db = Database("laporan_kerja.db")

    WorkReportHandlers(bot, db).register()

    print("Bot versi modular sedang berjalan...")
    bot.infinity_polling()


if __name__ == "__main__":
    main()