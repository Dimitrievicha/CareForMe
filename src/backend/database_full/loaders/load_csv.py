#!/usr/bin/env python3
"""Скрипт для загрузки данных из CSV в БД"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import get_db_manager
from database.raw_sql_loader import (
    load_plants_from_csv_raw,
    load_achievements_from_csv_raw,
    verify_data
)


def main():

    print("Создание таблиц...")
    db = get_db_manager()

    sql_path = Path(__file__).parent.parent / "database" / "init_db.sql"
    db.init_database_from_sql(str(sql_path))

    plant_csv = Path(__file__).parent.parent / "csv" / "plant_catalog.csv"
    load_plants_from_csv_raw(str(plant_csv))

    achievements_csv = Path(__file__).parent.parent / "csv" / "achievements_catalog.csv"
    load_achievements_from_csv_raw(str(achievements_csv))

    stats = verify_data()

    if stats['plants_count'] > 0:
        print("\n✅ Загрузка завершена успешно!")
    else:
        print("\n⚠️ Загрузка завершена с ошибками")


if __name__ == "__main__":
    main()