# Production Dockerfile for KhmerBeats Backend on Render
FROM python:3.11-slim-bookworm

# Python environment settings for reliable logging in Render console
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NODE_PATH=/app/node_modules

# Install Node.js 20 & curl for UploadThing UTApi service
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Node dependencies for UploadThing service
COPY package*.json ./
RUN npm install --omit=dev

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application files
COPY . .

# Default port for Render web services
ENV PORT=10000
EXPOSE 10000

# Start FastAPI server (supports running directly from repo root: main:app)
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
