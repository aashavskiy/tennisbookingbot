import os
import sqlite3
import logging
import pytesseract
from flask import Flask, request
import telebot
from PIL import Image
import io

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

def extract_booking_details(image_bytes):
    """Extracts date, time, club name, and court number from the booking screenshot."""
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert image to grayscale (improves OCR accuracy)
    image = image.convert("L")
    
    # Extract text using Tesseract
    extracted_text = pytesseract.image_to_string(image)

    print("Extracted text:", extracted_text)  # Debugging

    return extracted_text  # Temporary return full text

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

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    if str(message.chat.id) not in WHITE_LIST:
        bot.send_message(message.chat.id, "❌ You do not have access to this bot.")
        return
    
    # Get highest resolution image
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)

    # Process image with OCR
    extracted_text = extract_booking_details(file)

    bot.send_message(message.chat.id, f"📄 Extracted text:\n\n{extracted_text}")

if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
