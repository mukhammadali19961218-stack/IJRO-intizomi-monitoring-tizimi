# =========================================================================
# STAGE 1: Build React SPA Frontend
# =========================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# =========================================================================
# STAGE 2: Python FastAPI Production Server
# =========================================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL and Excel processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source code
COPY backend/ ./backend/
COPY assets/ ./assets/

# Copy built React frontend distribution
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure persistent directories exist
RUN mkdir -p /app/data/uploads/employees /app/data/tasks /app/database

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000

# Run FastAPI server with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
