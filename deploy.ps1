# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
# MyAgent - PowerShell Deployment Script (Port: 3399)
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 Starting MyAgent Installation & Deployment (Port: 3399)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: Docker is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Create persistent directories
Write-Host "📁 Creating persistent storage directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "data/documents" | Out-Null
New-Item -ItemType Directory -Force -Path "data/chroma_db" | Out-Null
New-Item -ItemType Directory -Force -Path "data/uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "data/backups" | Out-Null

# Check .env
if (-not (Test-Path ".env")) {
    Write-Host "⚙️ Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# Build and start
Write-Host "🔨 Building Docker images and starting services..." -ForegroundColor Yellow
docker compose down --remove-orphans
docker compose up -d --build

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "🎉 MyAgent Successfully Deployed!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "🌐 Web Interface:      http://localhost:3399 (or http://192.168.9.9:3399)" -ForegroundColor Cyan
Write-Host "🔑 Admin Username:     admin" -ForegroundColor Yellow
Write-Host "🔒 Admin Password:     Aa987654" -ForegroundColor Yellow
Write-Host "🔌 Backend API:        http://localhost:8000/api" -ForegroundColor Cyan
Write-Host "📖 Swagger API Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
docker compose ps
