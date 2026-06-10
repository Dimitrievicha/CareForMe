#!/usr/bin/env python3
"""Скрипт для загрузки данных из CSV в БД"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import get_db_manager
from database.raw_sql_loader import (
    load_plants_from_csv_raw,
    load_achievements_from_csv_raw,
    load_tips_from_csv_raw,
    load_level_requirements_from_csv_raw,
    verify_data
)


def main():
    print("=" * 50)
    print("Загрузка данных из CSV файлов в базу данных")
    print("=" * 50)

    print("\n1. Создание таблиц...")
    db = get_db_manager()
    sql_path = Path(__file__).parent.parent / "database" / "init_db.sql"

    if not sql_path.exists():
        print(f" SQL файл не найден: {sql_path}")
        return

    if db.init_database_from_sql(str(sql_path)):
        print("Таблицы созданы успешно")
    else:
        print("Ошибка при создании таблиц")
        return

    print("\n2. Загрузка шаблонов растений...")
    plant_csv = Path(__file__).parent.parent / "csv" / "plant_catalog.csv"
    if plant_csv.exists():
        load_plants_from_csv_raw(str(plant_csv))
    else:
        print(f"Файл не найден: {plant_csv}")

    print("\n3. Загрузка достижений...")
    achievements_csv = Path(__file__).parent.parent / "csv" / "achievements_catalog.csv"
    if achievements_csv.exists():
        load_achievements_from_csv_raw(str(achievements_csv))
    else:
        print(f"Файл не найден: {achievements_csv}")

    print("\n4. Загрузка советов...")
    tips_csv = Path(__file__).parent.parent / "csv" / "tips.csv"
    if tips_csv.exists():
        load_tips_from_csv_raw(str(tips_csv))
    else:
        print(f"Файл не найден: {tips_csv}")

    print("\n5. Загрузка заданий уровней...")
    level_csv = Path(__file__).parent.parent / "csv" / "level_requirements.csv"
    if level_csv.exists():
        load_level_requirements_from_csv_raw(str(level_csv))
    else:
        print(f"Файл не найден: {level_csv}")


    stats = verify_data()


    if stats['plants_count'] > 0 and stats['tips_count'] > 0 and stats['level_quests_count'] > 0:
        print("\nЗагрузка завершена успешно!")
    else:
        print("\nЗагрузка завершена TESTING_REPORT.md ошибками. Проверьте наличие CSV файлов.")


if __name__ == "__main__":
    main()