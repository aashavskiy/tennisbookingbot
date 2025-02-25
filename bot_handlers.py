# File: bot_handlers.py
# Telegram bot command handlers for the Tennis Booking Bot

import os
import telebot
import re
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
from sqlalchemy import text

# Initialize bot with specific configurations to prevent duplicate processing
bot = telebot.TeleBot(TOKEN, threaded=True, skip_pending=True)

# Storage for booking details
user_bookings = {}

# Track processed message IDs to prevent duplicate handling
processed_messages = set()
MAX_PROCESSED_MESSAGES = 1000  # Limit to prevent memory growth

@bot.message_handler(commands=['admin'])
def check_admin(message):
    """Checks and displays admin status of the requesting user"""
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
    user_id = str(message.from_user.id)
    username = message.from_user.username
    
    if is_user_admin(user_id):
        bot.reply_to(message, f"✅ User @{username} (ID: {user_id}) is an administrator.")
    else:
        bot.reply_to(message, f"❌ User @{username} (ID: {user_id}) is not an administrator.")
    
    # Limit the size of processed_messages set
    if len(processed_messages) > MAX_PROCESSED_MESSAGES:
        # Remove the oldest half of the messages
        processed_messages.clear()

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handles the /start command and user registration"""
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
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
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
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
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
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
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
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

@bot.message_handler(commands=['manual'])
def manual_booking(message):
    """Provides instructions for manual booking entry"""
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
    if not is_user_approved(str(message.from_user.id)):
        bot.reply_to(message, "⏳ Please wait for administrator approval before using the bot.")
        return
        
    bot.reply_to(
        message,
        "Please enter your booking in this format:\n\n"
        "date: 09/03/2025\n"
        "time: 19:00-20:00\n"
        "court: 14"
    )

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Handles received photos with button-based booking entry"""
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
    user_id = str(message.from_user.id)
    
    # Check user approval
    if not is_user_approved(user_id):
        bot.reply_to(message, "⏳ Please wait for administrator approval before using the bot.")
        return

    try:
        # Create a selection interface with buttons
        markup = telebot.types.InlineKeyboardMarkup()
        
        # Date selection button
        date_button = telebot.types.InlineKeyboardButton(
            text="📅 March 9, 2025", 
            callback_data="date_09/03/2025"
        )
        
        # Time selection button
        time_button = telebot.types.InlineKeyboardButton(
            text="🕗 19:00-20:00",
            callback_data="time_19:00-20:00"
        )
        
        # Court selection button
        court_button = telebot.types.InlineKeyboardButton(
            text="🎾 Court 14",
            callback_data="court_14"
        )
        
        # Save button
        save_button = telebot.types.InlineKeyboardButton(
            text="💾 Save Booking",
            callback_data="save_booking"
        )
        
        # Add buttons to markup
        markup.row(date_button)
        markup.row(time_button)
        markup.row(court_button)
        markup.row(save_button)
        
        # Send message with inline keyboard
        bot.reply_to(message, 
            "Please confirm your booking details:",
            reply_markup=markup)
            
    except Exception as e:
        logger.error(f"Error handling photo: {str(e)}")
        bot.reply_to(message, "❌ Error processing your request. Please try the /manual command.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('date_', 'time_', 'court_')))
def handle_booking_selection(call):
    """Handles selection of booking details"""
    user_id = str(call.from_user.id)
    
    # Initialize user's booking details if not exists
    if user_id not in user_bookings:
        user_bookings[user_id] = {'date': None, 'time': None, 'court': None}
    
    # Parse the selection
    data_type, value = call.data.split('_', 1)
    
    # Update booking details
    user_bookings[user_id][data_type] = value
    
    # Acknowledge the selection
    bot.answer_callback_query(call.id, f"{data_type.capitalize()} selected: {value}")
    
    # Update message with current selections
    details = user_bookings[user_id]
    message_text = "Please confirm your booking details:\n\n"
    message_text += f"📅 Date: {details['date'] or 'Not selected'}\n"
    message_text += f"🕒 Time: {details['time'] or 'Not selected'}\n"
    message_text += f"🎾 Court: {details['court'] or 'Not selected'}\n"
    
    bot.edit_message_text(
        text=message_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=call.message.reply_markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "save_booking")
def save_booking_callback(call):
    """Handles saving the booking"""
    user_id = str(call.from_user.id)
    
    # Acknowledge the button press immediately
    bot.answer_callback_query(call.id, "Processing your booking...")
    
    logger.info(f"Save booking button pressed by user {user_id}")
    
    if user_id not in user_bookings:
        logger.warning(f"No booking details found for user {user_id}")
        bot.answer_callback_query(call.id, "No booking details found")
        return
    
    details = user_bookings[user_id]
    logger.info(f"Retrieved booking details for user {user_id}: {details}")
    
    # Check if all details are provided
    if not details['date'] or not details['time'] or not details['court']:
        missing = []
        if not details['date']: missing.append("date")
        if not details['time']: missing.append("time")
        if not details['court']: missing.append("court")
        
        logger.warning(f"Incomplete booking details for user {user_id}. Missing: {', '.join(missing)}")
        bot.answer_callback_query(call.id, "Please select all booking details first")
        return
    
    # Save booking to database
    try:
        logger.info(f"Attempting to save booking for user {user_id} with details: {details}")
        
        success = save_booking(user_id, details['date'], details['time'], details['court'])
        
        if success:
            logger.info(f"Successfully saved booking for user {user_id}")
            
            # Update the message text
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ Booking saved successfully!\n\n"
                     f"📅 Date: {details['date']}\n"
                     f"🕒 Time: {details['time']}\n"
                     f"🎾 Court: {details['court']}"
            )
            
            # Clear temporary data
            del user_bookings[user_id]
        else:
            logger.error(f"Database operation failed when saving booking for user {user_id}")
            bot.answer_callback_query(call.id, "Failed to save booking to database")
            bot.send_message(call.message.chat.id, "❌ Failed to save booking to database. Please try again.")
    except Exception as e:
        logger.error(f"Error saving booking for user {user_id}: {str(e)}")
        bot.answer_callback_query(call.id, "An error occurred while processing your booking")
        bot.send_message(call.message.chat.id, "❌ An error occurred while processing your booking. Please try again.")

@bot.message_handler(func=lambda message: 
                    message.text and 
                    message.text.lower().startswith('date:') and 
                    'time:' in message.text.lower() and 
                    'court:' in message.text.lower())
def handle_manual_entry(message):
    """Processes manual booking entries"""
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
    user_id = str(message.from_user.id)
    
    if not is_user_approved(user_id):
        bot.reply_to(message, "⏳ Please wait for administrator approval before using the bot.")
        return
        
    try:
        text = message.text
        
        # Extract date
        date_match = re.search(r'date:\s*([\d/.-]+)', text, re.IGNORECASE)
        date = date_match.group(1) if date_match else None
        
        # Extract time
        time_match = re.search(r'time:\s*([\d:.-]+)', text, re.IGNORECASE)
        time_value = time_match.group(1) if time_match else None
        
        # Extract court
        court_match = re.search(r'court:\s*(\d+)', text, re.IGNORECASE)
        court = court_match.group(1) if court_match else None
        
        if date and time_value and court:
            # Save to database
            if save_booking(user_id, date, time_value, court):
                bot.reply_to(message, 
                    f"✅ Booking recorded successfully!\n\n"
                    f"📅 Date: {date}\n"
                    f"🕒 Time: {time_value}\n"
                    f"🎾 Court: {court}")
            else:
                bot.reply_to(message, "❌ Failed to save booking to database.")
        else:
            missing = []
            if not date: missing.append("date")
            if not time_value: missing.append("time")
            if not court: missing.append("court")
            
            bot.reply_to(message, 
                f"❌ Could not find all required information. Missing: {', '.join(missing)}\n\n"
                f"Please use the format:\n"
                f"date: 09/03/2025\n"
                f"time: 19:00-20:00\n"
                f"court: 14")
    except Exception as e:
        logger.error(f"Error in manual entry: {str(e)}")
        bot.reply_to(message, "❌ Error processing your entry. Please check the format and try again.")

# The default handler should be the last registered handler
@bot.message_handler(func=lambda message: True)
def check_access(message):
    """Default handler that checks user approval status"""
    # Check if message already processed
    if message.message_id in processed_messages:
        return
    processed_messages.add(message.message_id)
    
    if not is_user_approved(str(message.from_user.id)):
        bot.reply_to(message, "⏳ Please wait for administrator approval before using the bot.")
        return
    else:
        bot.reply_to(message, 
            "Send me a screenshot of your tennis court booking to save it, or use the /manual command to enter booking details manually.")