#!/usr/bin/env python3
"""
Скрипт загрузки данных из CSV файлов
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

print(f"Добавлен путь: {backend_dir}")
print(f"Текущий PYTHONPATH: {sys.path[0]}")

from database_full.database.db_manager import get_db_manager
from database_full.database.raw_sql_loader import (
        load_plants_from_csv_raw,
        load_achievements_from_csv_raw,
        load_tips_from_csv_raw,
        load_level_requirements_from_csv_raw,
    )


def load_csv_data():
    """Загружает все данные из CSV файлов"""

    db = get_db_manager()

    result = db.execute_query("SELECT COUNT(*) as count FROM plant_templates")

    if result and result[0]['count'] > 0:
        print("Данные уже загружены, пропускаем...")
        return True

    csv_dir = csv_dir = backend_dir / 'database_full' / 'csv'

    if not csv_dir.exists():
        print(f"Директория CSV не найдена: {csv_dir}")
        print(f"Создаю папку {csv_dir}...")
        csv_dir.mkdir(parents=True, exist_ok=True)
        print(f"Пожалуйста, поместите CSV файлы в папку: {csv_dir}")
        return False

    print("Загрузка данных из CSV файлов...")
    print(f"CSV директория: {csv_dir}")

    plant_csv = csv_dir / 'plant_catalog.csv'
    if plant_csv.exists():
        print("\nЗагрузка растений...")
        load_plants_from_csv_raw(str(plant_csv))
    else:
        print(f"Файл не найден: {plant_csv}")

    achievements_csv = csv_dir / 'achievements_catalog.csv'
    if achievements_csv.exists():
        print("\nЗагрузка достижений...")
        load_achievements_from_csv_raw(str(achievements_csv))
    else:
        print(f"Файл не найден: {achievements_csv}")

    tips_csv = csv_dir / 'tips.csv'
    if tips_csv.exists():
        print("\nЗагрузка советов...")
        load_tips_from_csv_raw(str(tips_csv))
    else:
        print(f"Файл не найден: {tips_csv}")

    level_csv = csv_dir / 'level_requirements.csv'
    if level_csv.exists():
        print("\nЗагрузка заданий уровней...")
        load_level_requirements_from_csv_raw(str(level_csv))
    else:
        print(f"Файл не найден: {level_csv}")

    print("\nРезультат загрузки:")

    stats = db.execute_query("""
        SELECT 
            (SELECT COUNT(*) FROM plant_templates) as plants,
            (SELECT COUNT(*) FROM achievements) as achievements,
            (SELECT COUNT(*) FROM tips) as tips,
            (SELECT COUNT(*) FROM level_requirements) as levels
    """)


    return True


if __name__ == "__main__":

    if load_csv_data():
        print("\nВсе данные успешно загружены!")
        sys.exit(0)
    else:
        print("\nОшибка загрузки данных")
        sys.exit(1)