#!/bin/sh
set -e

DB_FILE="/app/backend/careforme.db"

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "dev-secret-key-change-me" ]; then
    echo "ERROR: SECRET_KEY не задан или использует значение по умолчанию!"
    exit 1
fi

mkdir -p /app/backend

if [ ! -f "$DB_FILE" ] || [ ! -s "$DB_FILE" ]; then
    echo ">>> Инициализация базы данных..."
    cd /app/backend

    if [ -d "$DB_FILE" ]; then
        rm -rf "$DB_FILE"
    fi

    echo "  → Создание таблиц..."
    python scripts/init_db.py

    echo "  → Загрузка данных..."
    python scripts/load_csv_data.py

    echo ">>> Инициализация завершена!"
else
    echo ">>> База данных уже существует: $DB_FILE"
fi

echo ">>> Запуск сервера..."
cd /app/backend
exec python app.py