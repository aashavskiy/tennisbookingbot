import os
import sqlite3
import logging
from flask import Flask, request
import telebot
from dotenv import load_dotenv
load_dotenv()

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WHITE_LIST = set(os.getenv("WHITE_LIST", "").split(","))  # Allowed users' IDs
DATABASE = "bookings.db"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS bookings (
                            id INTEGER PRIMARY KEY,
                            user_id TEXT,
                            date TEXT,
                            time TEXT,
                            club TEXT,
                            court TEXT)''')
        conn.commit()

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "", 200

@bot.message_handler(commands=['start'])
def start_message(message):
    if str(message.chat.id) not in WHITE_LIST:
        bot.send_message(message.chat.id, "❌ You do not have access to this bot.")
        return
    bot.send_message(message.chat.id, "🎾 Hello! Send me a screenshot of your booking.")

@bot.message_handler(commands=['bookings'])
def all_bookings(message):
    if str(message.chat.id) not in WHITE_LIST:
        return
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT date, time, club, court FROM bookings")
        rows = cursor.fetchall()
        if not rows:
            bot.send_message(message.chat.id, "📭 No bookings found.")
            return
        response = "\n".join([f"📅 {date} {time} - {club} (Court {court})" for date, time, club, court in rows])
        bot.send_message(message.chat.id, response)

if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
