# Use official Python image
FROM python:3.11-slim

# Install Tesseract, language pack and OpenCV dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-heb \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set Tesseract data directory environment variable
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
ENV CLOUD_RUN=True

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the remaining project files
COPY . .

# Expose the port that Cloud Run will use
EXPOSE 8080

# Command to run the application
CMD exec python tennis_booking_bot.py