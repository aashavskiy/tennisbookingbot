#!/bin/bash
# Deployment script for Tennis Booking Bot to Google Cloud Run

# Configuration variables - change these to match your project
PROJECT_ID="your-gcp-project-id"
SERVICE_NAME="tennis-booking-bot"
REGION="eu-centrral2"  # change to your preferred region

# Build the container image
echo "Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},ADMIN_ID=${ADMIN_ID},WEBHOOK_URL=${WEBHOOK_URL}" \
  --memory 512Mi

# Get the deployed service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "Service deployed at: $SERVICE_URL"
echo "Webhook URL should be set to: $SERVICE_URL/${TELEGRAM_BOT_TOKEN}"

# Set the webhook to Telegram
echo "Setting webhook with Telegram..."
curl -F "url=${SERVICE_URL}/${TELEGRAM_BOT_TOKEN}" https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook

echo "Deployment complete!"