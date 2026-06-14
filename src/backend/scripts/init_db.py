#!/usr/bin/env python3
"""
Скрипт инициализации структуры базы данных
"""

import sys
from pathlib import Path

# Добавляем путь для импорта модулей backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from database_full.database.db_manager import get_db_manager

TABLES = [
    'users',
    'player_profiles',
    'plant_templates',
    'user_plants',
    'achievements',
    'level_requirements',
]

def init_database() -> bool:
    """Инициализирует структуру БД из SQL файла. Возвращает True при успехе."""

    # Путь к БД — рядом с app.py в папке backend/
    db_path = str(Path(__file__).parent.parent / 'careforme.db')
    db = get_db_manager(db_path)

    # Путь к SQL файлу (исправлен: database_full/database/)
    sql_path = Path(__file__).parent.parent / 'database_full' / 'database' / 'init_db.sql'

    if not sql_path.exists():
        print(f"SQL файл не найден: {sql_path}")
        return False

    print(f"Загрузка схемы БД из {sql_path}")

    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        conn = db.connect()
        conn.executescript(sql_script)
        # conn.commit()

        print("Структура БД успешно создана")

        for table in TABLES:
            exists = db.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            status = "OK" if exists else "NOT"
            print(f" {status} {table}")
       

    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False


if __name__ == "__main__":
    if init_database():
        print("База данных готова к работе!")
        sys.exit(0)
    else:
        print("\n Ошибка инициализации базы данных")
        sys.exit(1)
