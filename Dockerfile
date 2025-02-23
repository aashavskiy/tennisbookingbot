# Use official Python image
FROM python:3.11

# Install Tesseract and language data
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-heb \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port for Cloud Run
EXPOSE 8080

# Run the bot
CMD exec python tennis_booking_bot.py