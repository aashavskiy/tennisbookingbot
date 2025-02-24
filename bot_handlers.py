# File: bot_handlers.py
# Telegram bot command handlers for the Tennis Booking Bot

import os
import telebot
from config import TOKEN, ADMIN_ID, logger
from db import (
    db, 
    is_user_admin, 
    is_user_approved, 
    approve_user,
    get_users, 
    get_user_bookings, 
    save_booking,
    create_user,
    check_user_status
)
from image_processing import process_image, extract_booking_info
from sqlalchemy import text

# Initialize bot
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['admin'])
def check_admin(message):
    """Checks and displays admin status of the requesting user"""
    user_id = str(message.from_user.id)
    username = message.from_user.username
    
    if is_user_admin(user_id):
        bot.reply_to(message, f"✅ User @{username} (ID: {user_id}) is an administrator.")
    else:
        bot.reply_to(message, f"❌ User @{username} (ID: {user_id}) is not an administrator.")

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handles the /start command and user registration"""
    user_id = str(message.from_user.id)
    username = message.from_user.username
    
    if db is None:
        bot.reply_to(message, "⚠️ The bot is currently experiencing database connectivity issues. Please try again later.")
        return
    
    try:
        # Check if user exists and their approval status
        user_status = check_user_status(user_id)
        
        if user_status is None:
            # New user registration
            if create_user(user_id, username, is_admin=0, is_approved=0):
                # Notify admin about new user
                admin_markup = telebot.types.InlineKeyboardMarkup()
                approve_button = telebot.types.InlineKeyboardButton(
                    text="✅ Approve",
                    callback_data=f"approve_{user_id}"
                )
                admin_markup.add(approve_button)
                
                admin_message = (f"👤 New user registration request:\n"
                               f"ID: {user_id}\n"
                               f"Username: @{username}")
                
                bot.send_message(ADMIN_ID, admin_message, reply_markup=admin_markup)
                
                # Notify user about pending approval
                bot.reply_to(message, "👋 Welcome! Your access request has been sent to the administrator. "
                                    "Please wait for approval.")
            else:
                bot.reply_to(message, "Sorry, there was an error processing your registration. Please try again later.")
        elif user_status == 0:
            # Existing but not approved user
            bot.reply_to(message, "⏳ Your access request is still pending. Please wait for administrator approval.")
        else:
            # Approved user
            bot.reply_to(message, "✅ Welcome back! You can use the bot's features.")
    except Exception as e:
        logger.error(f"error handling start command: {str(e)}")
        bot.reply_to(message, "Sorry, there was an error processing your request. Please try again later.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def handle_approval(call):
    """Handles user approval from admin"""
    if not is_user_admin(str(call.from_user.id)):
        bot.answer_callback_query(call.id, "❌ You don't have permission to approve users.")
        return
    
    user_id = call.data.split('_')[1]
    if approve_user(user_id):
        # Notify admin
        bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    reply_markup=None)
        bot.edit_message_text(chat_id=call.message.chat.id,
                             message_id=call.message.message_id,
                             text=f"{call.message.text}\n\n✅ Approved!")
        
        # Notify approved user
        bot.send_message(user_id, "✅ Your access has been approved! You can now use the bot's features.")
    else:
        bot.answer_callback_query(call.id, "❌ There was an error approving the user.")

@bot.message_handler(commands=['users'])
def list_users(message):
    """Lists all registered users (admin only)"""
    if not is_user_admin(str(message.chat.id)):
        bot.send_message(message.chat.id, "❌ You do not have permission to view users.")
        return
    
    users = get_users()
    if not users:
        bot.send_message(message.chat.id, "📭 No users found.")
    else:
        response = "👤 Registered Users:\n"
        for user in users:
            admin_status = " (Admin)" if user[2] == 1 else ""
            approved_status = "✅ Approved" if user[3] == 1 else "⏳ Pending"
            response += f"🆔 {user[0]} - @{user[1]}{admin_status} - {approved_status}\n"
        bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['dbstatus'])
def db_status(message):
    """Checks and displays database connection status (admin only)"""
    if not is_user_admin(str(message.chat.id)):
        bot.send_message(message.chat.id, "❌ You do not have permission to check database status.")
        return
        
    if db is None:
        bot.send_message(message.chat.id, "❌ Database connection pool is not initialized.")
        return
        
    try:
        with db.connect() as conn:
            conn.execute(text("SELECT 1"))
            bot.send_message(message.chat.id, "✅ Database connection is working.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Database connection test failed: {str(e)}")

@bot.message_handler(commands=['bookings'])
def list_bookings(message):
    """Displays all bookings for the current user"""
    if not is_user_approved(str(message.from_user.id)):
        bot.reply_to(message, "⏳ Please wait for administrator approval before using the bot.")
        return
        
    bookings = get_user_bookings(str(message.from_user.id))
    if not bookings:
        bot.reply_to(message, "📭 You don't have any bookings yet.")
        return
        
    response = "📅 Your bookings:\n\n"
    for booking in bookings:
        response += f"Date: {booking[0]}\n"
        response += f"Time: {booking[1]}\n"
        response += f"Court: {booking[2]}\n"
        response += f"Added: {booking[3]}\n"
        response += "---------------\n"
    
    bot.reply_to(message, response)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Handles received photos and extracts booking information"""
    user_id = str(message.from_user.id)
    
    # Check user approval
    if not is_user_approved(user_id):
        bot.reply_to(message, "⏳ Please wait for administrator approval before using the bot.")
        return

    try:
        # Send acknowledgment
        bot.reply_to(message, "🔍 Processing your booking image...")
        
        # Get the file id of the largest photo
        file_id = message.photo[-1].file_id
        logger.info(f"Received photo with file_id: {file_id}")
        
        # Download the photo
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Save the photo temporarily
        temp_dir = "/tmp"  # use /tmp for cloud run
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        temp_file = os.path.join(temp_dir, f"temp_image_{user_id}.jpg")
        with open(temp_file, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Process the image
        extracted_text = process_image(temp_file)
        
        if extracted_text:
            # Send the extracted text to the user (for debugging)
            # Limit length to avoid message size issues
            debug_text = extracted_text[:2000] if len(extracted_text) > 2000 else extracted_text
            bot.send_message(message.chat.id, f"📄 Extracted text:\n\n{debug_text}")
            
            # Extract booking info
            date, time, court = extract_booking_info(extracted_text)
            
            # Show what was extracted
            bot.send_message(message.chat.id, 
                f"📋 Extracted booking details:\n"
                f"Date: {date or 'Not found'}\n"
                f"Time: {time or 'Not found'}\n"
                f"Court: {court or 'Not found'}")
            
            if date and time and court:
                # Save to database
                if save_booking(user_id, date, time, court):
                    bot.send_message(message.chat.id, 
                        f"✅ Booking recorded successfully!\n\n"
                        f"📅 Date: {date}\n"
                        f"🕒 Time: {time}\n"
                        f"🎾 Court: {court}")
                else:
                    bot.send_message(message.chat.id, "❌ Failed to save booking to database.")
            else:
                missing = []
                if not date: missing.append("date")
                if not time: missing.append("time")
                if not court: missing.append("court number")
                bot.send_message(message.chat.id, 
                    f"❌ Could not find all required information. Missing: {', '.join(missing)}")
        else:
            bot.send_message(message.chat.id, 
                "❌ Could not extract text from image. Please send a clearer image.")
            
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
    except Exception as e:
        logger.error(f"Error handling photo: {str(e)}")
        bot.send_message(message.chat.id, "❌ Error processing your image. Please try again.")

@bot.message_handler(func=lambda message: True)
def check_access(message):
    """Default handler that checks user approval status"""
    if not is_user_approved(str(message.from_user.id)):
        bot.reply_to(message, "⏳ Please wait for administrator approval before using the bot.")
        return
    else:
        bot.reply_to(message, "Send me a screenshot of your tennis court booking to save it.")