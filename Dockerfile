# Use official Python image
FROM python:3.11-slim

# Install Tesseract and dependencies (without Hebrew language pack)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for Cloud Run
ENV CLOUD_RUN=True

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY config.py db.py image_processing.py bot_handlers.py routes.py main.py ./

# Expose the port that Cloud Run will use
EXPOSE 8080

# Command to run the application with Gunicorn for reliability
CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 main:app