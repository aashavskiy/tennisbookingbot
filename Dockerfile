# Use official Python image
FROM python:3.11-slim

# Install Tesseract and verify Hebrew language pack installation
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-heb \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && ls -la /usr/share/tesseract-ocr/4.00/tessdata/ \
    && if [ ! -f /usr/share/tesseract-ocr/4.00/tessdata/heb.traineddata ]; then \
       echo "Hebrew language data not found, attempting manual installation"; \
       mkdir -p /usr/share/tesseract-ocr/4.00/tessdata/ && \
       apt-get update && \
       apt-get install -y wget && \
       wget -O /usr/share/tesseract-ocr/4.00/tessdata/heb.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/heb.traineddata; \
    fi

# Find and set the correct tesseract data path
RUN tesseract --list-langs || true && \
    find /usr -name "tessdata" -type d 2>/dev/null || true && \
    TESSDATA_DIR=$(find /usr -name "tessdata" -type d | head -1) && \
    echo "Found Tesseract data directory at: $TESSDATA_DIR" && \
    echo "export TESSDATA_PREFIX=$TESSDATA_DIR" >> /etc/profile

# Set environment variables
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

# Command to run the application with explicit environment variable
CMD TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata exec python tennis_booking_bot.py