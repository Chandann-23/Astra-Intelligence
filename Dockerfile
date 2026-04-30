# Build Trigger: LangGraph Astra v1
FROM python:3.12-slim

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Copy requirements first to leverage Docker cache
COPY backend/requirements.txt .

# 2. Install dependencies (Added --upgrade to ensure LangChain/LangGraph versions)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 3. Copy the backend source code
# Note: Based on your main.py, we need the folder structure to stay intact
COPY backend/ .

# Configuration for Hugging Face
ENV PORT=7860
ENV PYTHONUNBUFFERED=1
# Critical: This tells Python that /app (which contains your code) is the root
ENV PYTHONPATH=/app

EXPOSE 7860

# Phase 4: Final Launch
# Using --log-level info for production to keep logs clean, 
# but keeping your logic of app.main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]