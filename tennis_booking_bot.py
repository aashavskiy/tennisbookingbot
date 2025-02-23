import os
import sqlite3
import logging
import pytesseract
import re
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
    """Extracts text from the booking screenshot using OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("L")  # Convert image to grayscale for better OCR
        
        # Save image for debugging
        image.save("debug_image.png")

        extracted_text = pytesseract.image_to_string(image)

        print("Extracted text:", extracted_text)  # Log output

        return extracted_text if extracted_text.strip() else "No text recognized."
    except Exception as e:
        print(f"Error processing image: {e}")
        return f"Error: {e}"

def parse_booking_text(text):
    """Extracts court number, date, and time from the OCR text."""
    
    # Extract court number (usually a number at the beginning)
    court_match = re.search(r"\b\d{1,2}\b", text)
    court = court_match.group(0) if court_match else "Unknown"

    # Extract date (DD/MM/YYYY format)
    date_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", text)
    date = date_match.group(0) if date_match else "Unknown"

    # Extract time (HH:MM-HH:MM format)
    time_match = re.search(r"\b\d{2}:\d{2}-\d{2}:\d{2}\b", text)
    time = time_match.group(0) if time_match else "Unknown"

    return {"court": court, "date": date, "time": time}

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
    
    bot.send_message(message.chat.id, "📷 Processing your booking screenshot...")

    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        bot.send_message(message.chat.id, "✅ Image received, running OCR...")

        extracted_text = extract_booking_details(file)
        bot.send_message(message.chat.id, f"🔍 Extracted raw text:\n```
{extracted_text}
```", parse_mode="Markdown")

        parsed_data = parse_booking_text(extracted_text)
        bot.send_message(message.chat.id, "📊 Parsed data extracted, sending results...")

        response = (
            f"📅 **Date:** {parsed_data['date']}\n"
            f"⏰ **Time:** {parsed_data['time']}\n"
            f"🏟 **Court:** {parsed_data['court']}\n"
        )

        bot.send_message(message.chat.id, response, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error processing image: {e}")
        print(f"Error in handle_screenshot: {e}")

if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
