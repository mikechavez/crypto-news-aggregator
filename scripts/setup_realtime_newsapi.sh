#!/bin/bash
# Script to set up the realtime-newsapi service
set -e

# Configuration
REPO_URL="https://github.com/janlukasschroeder/realtime-newsapi.git"
TARGET_DIR="$HOME/realtime-newsapi"
SERVICE_NAME="realtime-newsapi"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install it first."
    echo "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
fi

echo "=== Setting up realtime-newsapi ==="

# Clone the repository if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    echo "Cloning realtime-newsapi repository..."
    git clone "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
else
    echo "Updating existing realtime-newsapi repository..."
    cd "$TARGET_DIR"
    git pull
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file with default configuration..."
    cat > .env <<EOL
# MongoDB configuration
MONGO_URI=mongodb://mongo:27017/news

# Redis configuration
REDIS_URI=redis://redis:6379/0

# API configuration
PORT=3000
HOST=0.0.0.0
NODE_ENV=development

# News sources (comma-separated)
SOURCES=coindesk,cointelegraph,decrypt,bitcoin-magazine,the-block

# Update interval in minutes (0 to disable)
UPDATE_INTERVAL=30

# Log level (error, warn, info, debug)
LOG_LEVEL=info
EOL
fi

# Start the service
echo "Starting realtime-newsapi service..."
docker-compose up -d

echo ""
echo "=== realtime-newsapi setup complete! ==="
echo "Service is now running at http://localhost:3000"
echo ""
echo "To check the logs:"
echo "  cd $TARGET_DIR && docker-compose logs -f"
echo ""
echo "To stop the service:"
echo "  cd $TARGET_DIR && docker-compose down"
echo ""
echo "To update the service in the future:"
echo "  cd $TARGET_DIR && git pull && docker-compose pull && docker-compose up -d --build"
echo ""
echo "You can now update your .env file to use the new service:"
echo "REALTIME_NEWSAPI_URL=http://localhost:3000"
echo ""
