FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .

RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

EXPOSE 8000 5005 5055