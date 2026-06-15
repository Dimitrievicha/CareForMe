FROM python:3.9-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 5000

# Healthcheck использует существующий API эндпоинт
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:5000/api/auth/verify || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]