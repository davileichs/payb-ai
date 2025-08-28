#!/bin/bash

# Integration Test Runner for Slack Bot AI Chat
# This script can be run manually by DevOps to test the system
# Docker containers must be started manually before running this script

set -e

echo "🚀 Starting Integration Test for Slack Bot AI Chat"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create it first."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if required containers are running
echo "🔍 Checking if Docker containers are running..."
if ! docker ps | grep -q "slack-ai-bot"; then
    echo "❌ Error: slack-ai-bot container is not running."
    echo "   Please start the containers first with: make docker-run"
    echo "   Or manually with: docker-compose -f docker/docker-compose.yml up -d"
    exit 1
fi

if ! docker ps | grep -q "slack-bot-redis"; then
    echo "❌ Error: slack-bot-redis container is not running."
    echo "   Please start the containers first with: make docker-run"
    echo "   Or manually with: docker-compose -f docker/docker-compose.yml up -d"
    exit 1
fi

echo "✅ Docker containers are running"

# Wait a bit for the application to be ready
echo "⏳ Waiting for application to be ready..."
sleep 5

# Run the integration test
echo "🧪 Running integration tests..."
python3 tests/integration_test.py
TEST_RESULT=$?

# Exit with test result
if [ $TEST_RESULT -eq 0 ]; then
    echo "🎉 Integration test completed successfully!"
    echo "ℹ️  Note: Docker containers are still running. Stop them manually if needed with: make docker-stop"
else
    echo "💥 Integration test failed!"
fi

exit $TEST_RESULT
