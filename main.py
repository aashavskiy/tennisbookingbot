# File: main.py
# Main application entry point for the Tennis Booking Bot

import os
from config import TOKEN, WEBHOOK_URL, PORT, logger
from db import initialize_db, init_db
from routes import app
from bot_handlers import bot
from image_processing import initialize_tesseract

def main():
    """Main function to start the bot"""
    try:
        # Log startup to verify execution
        logger.info("Starting Tennis Booking Bot application...")

        # Initialize Tesseract OCR
        initialize_tesseract()
        logger.info("Tesseract OCR initialized")
        
        # Initialize database connection - don't block startup if DB fails
        logger.info("Initializing database connection...")
        db = initialize_db()
        
        # Initialize database tables
        if db is not None:
            logger.info("Database connection successful, initializing tables...")
            db_init_success = init_db()
            if not db_init_success:
                logger.warning("Database initialization failed, but the bot will continue to run")
        else:
            logger.warning("Database connection failed, but the bot will continue to run")
            
        # Set webhook if WEBHOOK_URL is provided
        if WEBHOOK_URL:
            logger.info(f"Setting webhook to {WEBHOOK_URL}/{TOKEN}")
            bot.remove_webhook()
            webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
            bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook set to {webhook_url}")
        else:
            logger.warning("WEBHOOK_URL not provided. Running in local mode with polling.")
            # If no webhook URL, use polling instead (for local development)
            bot.remove_webhook()
            # Don't start polling here, it will block the web server
        
        # Start flask server
        logger.info(f"✅ Starting web server on port {PORT}...")
        return app
        
    except Exception as e:
        logger.error(f"Critical error in main function: {str(e)}")
        # Return the app anyway to allow health checks to work
        return app

# This is important for Cloud Run to find the WSGI application
# Don't add if __name__ == "__main__" to ensure it works with Gunicorn
app = main()