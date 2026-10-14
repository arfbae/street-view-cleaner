#!/bin/bash
set -e

echo "=========================================================="
echo "🚀 STARTING STREET-VIEW & INSTAGRAM CLEANER DEPLOYMENT"
echo "=========================================================="

# 1. Environment Validation
if [ ! -f .env ]; then
    echo "⚠️ Warning: .env file not found. Cloning from template configuration..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Template .env generated."
    else
        echo "❌ Error: Core template layouts missing. Execution stopped."
        exit 1
    fi
fi

# 2. Build Container Framework
echo "⏳ Spinning up Docker infrastructure containers..."
docker-compose up --build -d

# 3. Dynamic Health Checking
echo "⏳ Monitoring microservice target channels..."
for i in {1..10}; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' street-view-cleaner-backend 2>/dev/null || echo "starting")
    if [ "$STATUS" = "healthy" ]; then
        echo -e "\n=========================================================="
        echo "🎉 DEPLOYMENT SUCCESSFUL!"
        echo "➔ Frontend: http://localhost"
        echo "➔ Backend Engine: http://localhost:8000"
        echo "=========================================================="
        exit 0
    fi
    echo "⏳ System status: ($STATUS)... Checking again soon."
    sleep 3
done

echo "❌ Error: Core API server failed to establish stable configuration within window frame."
docker-compose logs backend
exit 1
