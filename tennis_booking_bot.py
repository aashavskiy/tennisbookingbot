import os
import sqlite3
import logging
import pytesseract
import re
import cv2
import numpy as np
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
                            court TEXT)''')
        conn.commit()

def save_booking(user_id, date, time, court):
    """Saves the booking details to the database."""
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO bookings (user_id, date, time, court) VALUES (?, ?, ?, ?)",
                (user_id, date, time, court),
            )
            conn.commit()
            print(f"✅ Booking saved: {date} {time}, Court {court}")
    except Exception as e:
        print(f"❌ Database error: {e}")

def extract_booking_details(image_bytes):
    """Extracts text from the booking screenshot using OCR with image preprocessing."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("L")  # Convert image to grayscale for better OCR

        # Convert PIL image to OpenCV format
        image_cv = np.array(image)
        image_cv = cv2.adaptiveThreshold(image_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)

        # Convert back to PIL for Tesseract
        processed_image = Image.fromarray(image_cv)

        # Run OCR
        extracted_text = pytesseract.image_to_string(processed_image, lang="eng")

        print("Extracted text:", extracted_text)  # Log output

        return extracted_text if extracted_text.strip() else "No text recognized."
    except Exception as e:
        print(f"Error processing image: {e}")
        return f"Error: {e}"

def parse_booking_text(text):
    """Extracts court number, date, and time from the OCR text using line-based logic."""
    
    # Split text into lines
    lines = text.split("\n")
    
    date, time, court = "Unknown", "Unknown", "Unknown"
    
    for i, line in enumerate(lines):
        # Find date (DD/MM/YYYY)
        if re.search(r"\b\d{2}/\d{2}/\d{4}\b", line):
            date = re.search(r"\b\d{2}/\d{2}/\d{4}\b", line).group(0)
            
            # The number before the date in the previous line is likely the court number
            if i > 0:
                possible_court = re.findall(r"\b\d{1,2}\b", lines[i - 1])
                if possible_court:
                    court = possible_court[-1]  # Take the last number before the date

        # Find time (HH:MM-HH:MM)
        if re.search(r"\b\d{2}:\d{2}-\d{2}:\d{2}\b", line):
            time = re.search(r"\b\d{2}:\d{2}-\d{2}:\d{2}\b", line).group(0)
    
    return {"court": court, "date": date, "time": time}

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handles incoming updates from Telegram."""
    update = request.get_json()
    print(f"📩 Incoming update: {update}")  # Debug log
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    print("✅ Update processed")
    return "", 200

@bot.message_handler(commands=['start'])
def start_message(message):
    print(f"✅ Received /start from {message.chat.id}")  # Debug log
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
        cursor.execute("SELECT date, time, court FROM bookings WHERE user_id = ?", (str(message.chat.id),))
        rows = cursor.fetchall()
        if not rows:
            bot.send_message(message.chat.id, "📭 No bookings found.")
            return
        response = "\n".join([f"📅 {date} {time} - Court {court}" for date, time, court in rows])
        bot.send_message(message.chat.id, response)

if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    port = int(os.environ.get("PORT", 8080))
    print(f"✅ Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)