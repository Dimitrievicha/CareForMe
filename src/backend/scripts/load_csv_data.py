#!/usr/bin/env python3
"""
Скрипт загрузки данных из CSV файлов
"""

import sys
from pathlib import Path

# Добавляем корневую директорию backend в путь поиска модулей
# Определяем путь к папке backend (родительская для scripts)
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database_full.database.db_manager import get_db_manager
from database_full.database.raw_sql_loader import (
        load_plants_from_csv_raw,
        load_achievements_from_csv_raw,
        load_tips_from_csv_raw,
        load_level_requirements_from_csv_raw,
    )

DB_PATH = str(backend_dir / 'careforme.db')

def load_csv_data() -> bool:
    """Загружает все данные из CSV файлов. Возвращает True при успехе."""

    db = get_db_manager(DB_PATH)

    # Проверяем, есть ли уже данные
    result = db.execute_query("SELECT COUNT(*) as count FROM plant_templates")

    if result and result[0]['count'] > 0:
        return True

    # Путь к CSV файлам (папка csv в корне backend)
    csv_dir = backend_dir / 'database_full' / 'csv'

    if not csv_dir.exists():
        csv_dir.mkdir(parents=True, exist_ok=True)
        return False


    files = {
        'plant_catalog.csv': ('Растений',load_plants_from_csv_raw),
        'achievements_catalog.csv': ('Достижений',load_achievements_from_csv_raw),
        'tips.csv': ('Советов',load_tips_from_csv_raw),
        'level_requirements.csv': ('Заданий уровней',load_level_requirements_from_csv_raw),
    }
    
    for filename, (label, loader) in files.items():
        path = csv_dir / filename
        if path.exists():
            loader(str(path))
        else:
            print(f"Файл не найден: {path}")


    stats = db.execute_query("""
        SELECT 
            (SELECT COUNT(*) FROM plant_templates) as plants,
            (SELECT COUNT(*) FROM achievements) as achievements,
            (SELECT COUNT(*) FROM tips) as tips,
            (SELECT COUNT(*) FROM level_requirements) as levels
    """)

    if stats:
        s = stats[0]
        print(f"  🌱 Растений: {stats[0]['plants']}")
        print(f"  🏆 Достижений: {stats[0]['achievements']}")
        print(f"  💡 Советов: {stats[0]['tips']}")
        print(f"  📋 Заданий уровней: {stats[0]['levels']}")

    return True


if __name__ == "__main__":

    if load_csv_data():
        print("\n✅ Все данные успешно загружены!")
        sys.exit(0)
    else:
        print("\n❌ Ошибка загрузки данных")
        sys.exit(1)