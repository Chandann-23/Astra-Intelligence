# Build Trigger: Gemini Sync v1
FROM python:3.12-slim

# Install system dependencies for build (Required for CrewAI/pydantic)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Copy requirements first from the backend folder to the container
COPY backend/requirements.txt .

# 2. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of the backend source code into the container
COPY backend/ .

# Hugging Face uses port 7860
ENV PORT=7860
EXPOSE 7860

# Run using uvicorn with debug logging
# Note: Since we copied the contents of /backend into /app, 
# 'app.main:app' assumes there is a folder named 'app' inside 'backend'.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "debug"]