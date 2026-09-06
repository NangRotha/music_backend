# KhmerBeats - Music Store Backend API

FastAPI backend for KhmerBeats Music Store with Telegram Checkout, Promo Codes, Banner Slides, and Admin CMS.

## Features
- 🚀 **FastAPI**: Fast, asynchronous Python REST API.
- 🗄️ **Database Support**: Out-of-the-box support for SQLite and PostgreSQL (Render, Supabase, Neon).
- ☁️ **UploadThing Integration**: Cloud media and image uploads via UploadThing v7 UTApi.
- 🔐 **JWT Auth**: Secure Bearer token authentication with pbkdf2 password hashing.
- 🌐 **CORS**: Configured for seamless communication with React/Vite frontends.
- 🚢 **Render Ready**: Includes `Dockerfile`, `render.yaml`, and healthcheck probes for 1-click deployment.

## Deployment on Render
See `render.yaml` or deploy as Docker/Python Web Service:
- **Build Command**: `bash render-build.sh` (or Docker)
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/health`
