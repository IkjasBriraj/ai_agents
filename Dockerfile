# Dockerfile for SeniorAgent Orchestrator
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install Node.js & system utilities
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    procps \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN cd /app/backend && pip install --no-cache-dir -r requirements.txt

# Copy frontend source and build static frontend bundle
COPY frontend /app/frontend
RUN cd /app/frontend && npm install && npm run build

# Copy remaining backend source
COPY backend /app/backend

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Environment variables
ENV USE_MONGODB=true
ENV MONGODB_URL=mongodb://mongodb:27017/senior_agent

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
