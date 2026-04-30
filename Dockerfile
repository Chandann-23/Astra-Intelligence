FROM python:3.12-slim

# Install system dependencies for build
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Hugging Face uses port 7860
ENV PORT=7860
EXPOSE 7860

# Run using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
