# Use official Python image
FROM python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for Cloud Run
EXPOSE 8080

# Command to run the bot and Flask server
CMD exec python tennis_booking_bot.py