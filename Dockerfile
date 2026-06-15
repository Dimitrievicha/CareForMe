FROM python:3.9-slim

# Установка curl для healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь backend код (с сохранением структуры)
COPY backend/ ./backend/

# Копируем фронтенд на уровень выше (чтобы /app/frontend существовал)
COPY frontend/ ./frontend/

# Копируем entrypoint
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 5000

# Healthcheck через curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]