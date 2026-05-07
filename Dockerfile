FROM python:3.11-slim

WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


# Install uv
RUN pip install --no-cache-dir uv


# Copy requirements first for better Docker cache
COPY requirements.txt .


# Install Python dependencies
RUN uv pip install --system --no-cache -r requirements.txt


# Copy project files
COPY . .


# Expose FastAPI port
EXPOSE 8000


# Start FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]