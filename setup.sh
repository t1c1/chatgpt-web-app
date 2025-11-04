#!/bin/bash

# ChatGPT Web App Setup Script

set -e

echo "🚀 Setting up ChatGPT Web App..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file from template
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your configuration."
    echo "   Important: Change the SECRET_KEY and database passwords!"
    echo ""
    read -p "Press Enter after configuring .env file..."
fi

# Generate a secure secret key if not set
if ! grep -q "^SECRET_KEY=.*[a-zA-Z0-9]" .env; then
    echo "🔐 Generating secure secret key..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/^SECRET_KEY=.*$/SECRET_KEY=$SECRET_KEY/" .env
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p uploads
mkdir -p logs

# Start the application
echo "🐳 Starting Docker containers..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ ChatGPT Web App is running!"
    echo ""
    echo "🌐 Access the web interface at: http://localhost:8000"
    echo "📚 API documentation at: http://localhost:8000/docs"
    echo ""
    echo "📊 Database: PostgreSQL on localhost:5432"
    echo "💾 Redis: localhost:6379"
    echo ""
    echo "🛑 To stop: docker-compose down"
    echo "📝 To view logs: docker-compose logs -f"
else
    echo "❌ Failed to start services. Check logs with: docker-compose logs"
    exit 1
fi

echo ""
echo "🎉 Setup complete! Happy searching! 🚀"




