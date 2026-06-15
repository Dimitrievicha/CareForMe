#!/bin/sh
set -e

DB_FILE="/app/backend/careforme.db"

echo "=== Care For Me ==="

# Проверка обязательного секрета
if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "dev-secret-key-change-me" ]; then
    echo "ERROR: SECRET_KEY не задан или использует значение по умолчанию!"
    exit 1
fi

# Папка для БД
mkdir -p /app/backend

# Проверка существования БД и инициализация
if [ ! -f "$DB_FILE" ] || [ ! -s "$DB_FILE" ]; then
    echo ">>> Инициализация базы данных..."
    cd /app/backend

    # Удаляем если это папка
    if [ -d "$DB_FILE" ]; then
        rm -rf "$DB_FILE"
    fi

    # Создаём структуру БД
    echo "  → Создание таблиц..."
    python scripts/init_db.py

    # Загружаем данные из CSV
    echo "  → Загрузка данных..."
    python scripts/load_csv_data.py

    echo ">>> Инициализация завершена!"
else
    echo ">>> База данных уже существует: $DB_FILE"
fi

echo ">>> Запуск сервера..."
cd /app/backend
exec python app.py
