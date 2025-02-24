# File: config.py
# Configuration settings and environment variables for the Tennis Booking Bot

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Telegram Bot configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "100013433")  # Default to your ID if not set in env
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8080))

# Log the admin ID for debugging
print(f"ADMIN_ID configured as: {ADMIN_ID}")

# Google Cloud SQL configuration
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")  # project:region:instance

# Validate required configuration
if not TOKEN:
    raise ValueError("❌ ERROR: TELEGRAM_BOT_TOKEN is not set. Check your .env file or environment variables!")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log important configuration
logger.info(f"Starting with ADMIN_ID: {ADMIN_ID}")

# Cloud environment detection
IS_CLOUD_RUN = os.environ.get("CLOUD_RUN", False)