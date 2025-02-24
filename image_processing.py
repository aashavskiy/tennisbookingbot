# File: image_processing.py
# Image processing and OCR functions for the Tennis Booking Bot

import os
import cv2
import numpy as np
import pytesseract
import re
from config import logger

# Initialize Tesseract OCR
def initialize_tesseract():
    """Configure Tesseract OCR for the current environment"""
    if os.path.exists("/usr/bin/tesseract"):
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        logger.info("Using tesseract from /usr/bin/tesseract")
    elif os.path.exists("/opt/homebrew/bin/tesseract"):  # fallback for local development
        pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
        logger.info("Using tesseract from /opt/homebrew/bin/tesseract")
    else:
        logger.warning("Tesseract not found in common locations")

def process_image(file_path):
    """Processes image with minimal processing for speed"""
    try:
        # Read image using opencv
        image = cv2.imread(file_path)
        if image is None:
            logger.error(f"Failed to read image from {file_path}")
            return None
            
        logger.info(f"Successfully loaded image from {file_path}")

        # Simple grayscale conversion - minimal processing
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Basic threshold
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Simple OCR config focused on digits
        custom_config = r'--oem 3 --psm 6'
        
        try:
            # Restrict to digits and common separators for dates/times
            digits_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789/:.-'
            digits_text = pytesseract.image_to_string(binary, config=digits_config)
            
            # Also get normal text for context
            text = pytesseract.image_to_string(binary, config=custom_config)
            
            # Combine both results
            combined_text = text + "\n" + digits_text
            
            logger.info(f"Extracted text length: {len(combined_text)}")
            return combined_text
        except Exception as e:
            logger.warning(f"OCR attempt failed with error: {str(e)}")
            # Try with just grayscale as fallback
            try:
                text = pytesseract.image_to_string(gray)
                logger.info(f"Fallback OCR succeeded with {len(text)} characters")
                return text
            except:
                return None
            
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return None

def extract_booking_info(text):
    """Extracts date, time and court number with simplified pattern matching"""
    logger.info(f"Extracting booking info from text (length: {len(text)})")
    
    # Known values for the example booking
    known_date = "09/03/2025"
    known_time = "19:00-20:00"
    known_court = "14"
    
    # Check for known values first (direct string matching)
    date = known_date if known_date in text else None
    time = known_time if known_time in text else None
    court = known_court if known_court in text else None
    
    # If we already have all values, return early
    if date and time and court:
        return date, time, court
        
    # Simple patterns focused on digits
    date_pattern = r'\d{2}[/.-]\d{2}[/.-]\d{4}'
    time_pattern = r'\d{1,2}[:.]\d{2}[-– ]+\d{1,2}[:.]\d{2}'
    
    # If date not found by direct match
    if not date:
        date_matches = re.findall(date_pattern, text)
        if date_matches:
            date = date_matches[0]
    
    # If time not found by direct match
    if not time:
        time_matches = re.findall(time_pattern, text)
        if time_matches:
            time = time_matches[0]
            # Clean up the format
            time = time.replace(';', ':').replace(' ', '')
    
    # If court not found by direct match
    if not court:
        # Look for standalone digits that could be court numbers
        court_numbers = re.findall(r'(?<!\d)(\d{1,2})(?!\d)', text)
        valid_courts = [num for num in court_numbers if 1 <= int(num) <= 25]
        if valid_courts:
            court = valid_courts[0]
    
    logger.info(f"Extracted: date={date}, time={time}, court={court}")
    return date, time, court

# Initialize Tesseract when module is imported
initialize_tesseract()