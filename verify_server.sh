#!/bin/bash
# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.0.0
# MyAgent - Server 192.168.9.9 Diagnostic and Health Verification Script
# ==============================================================================

echo "=========================================================="
echo "🔍 Running MyAgent Health Diagnostics (192.168.9.9:3399)"
echo "=========================================================="

# 1. Check Docker service
if docker ps &> /dev/null; then
    echo "✅ Docker Engine is running."
else
    echo "❌ Docker Engine is not accessible."
    exit 1
fi

# 2. Check running containers
echo "📊 Checking MyAgent Containers:"
docker ps --filter "name=myagent" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 3. Check Backend Health
echo ""
echo "🔌 Testing Backend API Health (Port 8000):"
HEALTH_RES=$(curl -s http://localhost:8000/api/health || echo "FAILED")
echo "Response: $HEALTH_RES"

# 4. Check Web Portal (Port 3399)
echo ""
echo "🌐 Testing Web Frontend (Port 3399):"
HTTP_STATUS=$(curl -o /dev/null -s -w "%{http_code}\n" http://localhost:3399 || echo "FAILED")
echo "HTTP Status: $HTTP_STATUS"

# 5. Test Admin Login with credentials (admin / Aa987654)
echo ""
echo "🔑 Testing Admin Authentication API:"
LOGIN_RES=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Aa987654"}')

if echo "$LOGIN_RES" | grep -q "access_token"; then
    echo "✅ Admin Login Test PASSED (JWT Token Issued)."
else
    echo "❌ Admin Login Test FAILED. Response: $LOGIN_RES"
fi

echo "=========================================================="
echo "🎯 Verification Complete. Access at: http://192.168.9.9:3399"
echo "=========================================================="
