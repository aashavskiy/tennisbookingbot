import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get bot token and webhook URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL:
    print("Error: TELEGRAM_BOT_TOKEN or WEBHOOK_URL is not set in .env file.")
    exit(1)

# Set webhook
set_webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/{TOKEN}"
response = requests.post(set_webhook_url)

# Print result
print("Webhook setup response:", response.json())

# Get webhook info
get_webhook_url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
response = requests.get(get_webhook_url)

# Print webhook info
print("Webhook info:", response.json())