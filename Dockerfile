# Python 3.11 slim base image ашиглах
FROM python:3.11-slim

# Working directory тохируулах
WORKDIR /app

# System dependencies суулгах (зарим Python packages-д хэрэгтэй)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Requirements файлыг эхлээд хуулж, dependencies суулгах (Docker layer caching-д сайн)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application кодыг хуулах
COPY . .

# Port expose хийх (config.py-д PORT = 3978 гэж заасан)
EXPOSE 3978

# Environment variables тохируулах (default values)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check нэмэх (FastAPI-ийн /health endpoint ашиглах)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3978/health || exit 1

# Application ажиллуулах
CMD ["python", "app.py"] 