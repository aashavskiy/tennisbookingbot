# File: routes.py
# Flask routes for the Tennis Booking Bot web service

from flask import Flask, request, Response
import telebot
from sqlalchemy import text
from config import TOKEN, logger
from db import db
from bot_handlers import bot

app = Flask(__name__)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Handles telegram webhook requests"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return Response('', status=200)
    else:
        return Response('', status=403)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for cloud run"""
    if db is None:
        return Response('Bot is running but database connection is not available', status=500)
        
    try:
        # Check database connection
        with db.connect() as conn:
            conn.execute(text("SELECT 1"))
        return Response('Bot is running with database connection', status=200)
    except Exception as e:
        logger.error(f"health check failed: {str(e)}")
        return Response(f'Bot is running but database connection failed: {str(e)}', status=500)

@app.route('/dbinfo', methods=['GET'])
def db_info():
    """Diagnostic endpoint for database information"""
    from config import DB_HOST, DB_NAME, INSTANCE_CONNECTION_NAME, IS_CLOUD_RUN
    
    if "admin" not in request.args.get("key", ""):
        return Response('Unauthorized', status=403)
        
    try:
        info = {
            "db_host": DB_HOST,
            "db_name": DB_NAME,
            "instance_name": INSTANCE_CONNECTION_NAME,
            "socket_path": f"/cloudsql/{INSTANCE_CONNECTION_NAME}",
            "cloud_run": IS_CLOUD_RUN
        }
        return Response(str(info), status=200)
    except Exception as e:
        return Response(f'Error: {str(e)}', status=500)

@app.route('/', methods=['GET'])
def index():
    """Root endpoint for cloud run"""
    return Response('Tennis Booking Bot is active', status=200)