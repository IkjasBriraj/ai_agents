#!/bin/bash
set -e

echo "=== SeniorAgent Orchestrator Starting ==="

# Check if local mongod exists (for standalone container execution)
if [ "$MONGODB_URL" = "mongodb://127.0.0.1:27017/senior_agent" ] || [ "$MONGODB_URL" = "mongodb://localhost:27017/senior_agent" ]; then
    if command -v mongod > /dev/null; then
        echo "-> Starting local MongoDB service..."
        mkdir -p /data/db
        mongod --fork --logpath /var/log/mongodb.log --dbpath /data/db || true
    fi
fi

echo "-> Starting FastAPI Backend & Frontend Server on port 8000..."
cd /app/backend
exec python main.py
