#!/bin/bash

# Slack Bot AI Chat Deployment Script
# This script helps deploy the application to production

set -e

echo "🚀 Starting Slack Bot AI Chat deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy env.example to .env and configure your settings."
    exit 1
fi

# Build Docker image
echo "🔨 Building Docker image..."
docker build -f docker/Dockerfile -t slack-ai-bot:latest .

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker/docker-compose.yml down || true

# Start new containers
echo "🚀 Starting new containers..."
docker-compose -f docker/docker-compose.yml up -d

# Wait for health check
echo "⏳ Waiting for application to be healthy..."
sleep 10

# Check health
HEALTH_CHECK=$(curl -s http://localhost:8000/health || echo "unhealthy")
if [[ $HEALTH_CHECK == *"healthy"* ]]; then
    echo "✅ Application is healthy and running!"
    echo "🌐 API available at: http://localhost:8000"
    echo "📚 API documentation at: http://localhost:8000/docs"
    echo "🔗 Slack webhook at: http://localhost:8000/slack"
else
    echo "❌ Application health check failed!"
    echo "📋 Checking logs..."
    docker-compose -f docker/docker-compose.yml logs --tail=20
    exit 1
fi

echo "🎉 Deployment completed successfully!"
