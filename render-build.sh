#!/usr/bin/env bash
# Render Build Script for Native Python Web Service
set -o errexit

echo "📦 Upgrading pip..."
pip install --upgrade pip

echo "📦 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# If Node / npm is installed in the environment, install node dependencies for UploadThing
if command -v npm &> /dev/null; then
    echo "📦 Installing Node dependencies for UploadThing UTApi..."
    npm install --omit=dev
else
    echo "ℹ️  npm not detected. Uploads will use local storage fallback or UploadThing HTTP API."
fi

echo "✅ Render build completed successfully!"
