#!/bin/bash
# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
# MyAgent - Deployment Script for Server 192.168.9.9 (Port: 3399)
# ==============================================================================

set -e

echo "=========================================================="
echo "🚀 Starting MyAgent Installation & Deployment on 192.168.9.9"
echo "🌐 Web Port: 3399 | Admin User: admin"
echo "=========================================================="

# 1. Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed on this system."
    echo "👉 Please install Docker: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 2. Check Docker Compose (v2 or v1)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "❌ Error: Docker Compose is not installed."
    echo "👉 Please install docker-compose-plugin."
    exit 1
fi

# 3. Create persistent directories
echo "📁 Creating persistent storage directories..."
mkdir -p data/documents
mkdir -p data/chroma_db
mkdir -p data/uploads
chmod -R 775 data/

# 4. Check .env file
if [ ! -f .env ]; then
    echo "⚙️ Creating .env configuration from template..."
    cp .env.example .env
    echo "✅ Created .env with Port 3399 and Admin credentials."
else
    echo "✅ Found existing .env configuration."
fi

# 5. Build and run containers
echo "🔨 Building Docker images and starting services on port 3399..."
$DOCKER_COMPOSE_CMD down --remove-orphans || true
$DOCKER_COMPOSE_CMD up -d --build

# 6. Wait for healthcheck
echo "⏳ Waiting for backend to initialize and warm up memory..."
sleep 8

echo "=========================================================="
echo "🎉 MyAgent Successfully Deployed!"
echo "=========================================================="
echo "🌐 Web Interface:      http://192.168.9.9:3399"
echo "🔑 Admin Username:     admin"
echo "🔒 Admin Password:     Aa987654"
echo "🔌 Backend API:        http://192.168.9.9:8000/api"
echo "📖 Swagger API Docs:   http://192.168.9.9:8000/docs"
echo "=========================================================="
echo "📊 Current Container Status:"
$DOCKER_COMPOSE_CMD ps
echo "=========================================================="
echo "💡 To view logs: $DOCKER_COMPOSE_CMD logs -f"
echo "💡 To stop:      $DOCKER_COMPOSE_CMD down"
