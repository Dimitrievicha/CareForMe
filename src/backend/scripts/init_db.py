#!/usr/bin/env python3
"""
Скрипт инициализации структуры базы данных
"""

import sys
import os
from pathlib import Path
from database.db_manager import get_db_manager


def init_database():
    """Инициализирует структуру БД из SQL файла"""

    # Добавляем путь для импорта модулей
    sys.path.insert(0, str(Path(__file__).parent.parent))

    db = get_db_manager()

    # Путь к SQL файлу
    sql_path = Path(__file__).parent.parent / 'database' / 'init_db.sql'

    if not sql_path.exists():
        print(f"❌ Файл {sql_path} не найден")
        return False

    print(f"📂 Загрузка схемы БД из {sql_path}")

    try:
        # Выполняем SQL скрипт
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # Разделяем скрипт на отдельные команды
        # (простой способ - выполнить весь скрипт целиком)
        conn = db.connect()
        conn.executescript(sql_script)
        conn.commit()

        print("✅ Структура БД успешно создана")

        # Проверяем создание таблиц
        tables = ['users', 'player_profiles', 'plant_templates', 'user_plants',
                  'achievements', 'level_requirements', 'designs']

        for table in tables:
            result = db.execute_query(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if result:
                print(f"  ✓ Таблица {table} создана")
            else:
                print(f"  ⚠️ Таблица {table} не найдена")

        return True

    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        if db._connection:
            db._connection.rollback()
        return False


if __name__ == "__main__":
    if init_database():
        print("🎉 База данных готова к работе!")
        sys.exit(0)
    else:
        print("💥 Ошибка инициализации базы данных")
        sys.exit(1)