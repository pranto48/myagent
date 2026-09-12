# ==============================================================================
# MyAgent - PowerShell Deployment Script
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 Starting MyAgent Installation & Deployment" -ForegroundColor Cyan
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
Write-Host "🌐 Web Interface:      http://localhost:3000 (or http://192.168.9.9:3000)" -ForegroundColor Cyan
Write-Host "🔌 Backend API:        http://localhost:8000/api" -ForegroundColor Cyan
Write-Host "📖 Swagger API Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
docker compose ps
