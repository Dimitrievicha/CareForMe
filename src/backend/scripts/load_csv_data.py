#!/usr/bin/env python3
"""
Скрипт загрузки данных из CSV файлов в базу данных.
Запускать из любой директории: py scripts/load_csv_data.py
"""

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).parent.parent
_DB_PATH     = _BACKEND_DIR / 'careforme.db'
_SQL_PATH    = _BACKEND_DIR / 'database_full' / 'database' / 'init_db.sql'

sys.path.insert(0, str(_BACKEND_DIR))

from database_full.database.db_manager import get_db_manager
from database_full.database.raw_sql_loader import (
    load_plants_from_csv_raw,
    load_achievements_from_csv_raw,
    load_tips_from_csv_raw,
    load_level_requirements_from_csv_raw,
)


def load_csv_data() -> bool:
    """Инициализирует схему БД и загружает все данные из CSV. Возвращает True при успехе."""
    db = get_db_manager(str(_DB_PATH))

    if not _SQL_PATH.exists():
        print(f" SQL файл не найден: {_SQL_PATH}")
        return False

    with open(_SQL_PATH, encoding='utf-8') as f:
        db.connect().executescript(f.read())

    # Если данные уже загружены — пропускаем
    result = db.execute_query("SELECT COUNT(*) as count FROM plant_templates")
    if result and result[0]['count'] > 0:
        return True

    csv_dir = _BACKEND_DIR / 'database_full' / 'csv'
    if not csv_dir.exists():
        print(f" Директория CSV не найдена: {csv_dir}")
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

    # Итоговая статистика
    stats = db.execute_query("""
        SELECT
            (SELECT COUNT(*) FROM plant_templates) AS plants,
            (SELECT COUNT(*) FROM achievements) AS achievements,
            (SELECT COUNT(*) FROM tips) AS tips,
            (SELECT COUNT(*) FROM level_requirements) AS levels
        """)

    if stats:
        s = stats[0]
        print(f"\n Результат загрузки:")
        print(f"  🌱 Растений:         {s['plants']}")
        print(f"  🏆 Достижений:       {s['achievements']}")
        print(f"  💡 Советов:          {s['tips']}")
        print(f"  📋 Заданий уровней:  {s['levels']}")

    return True


if __name__ == "__main__":

    if load_csv_data():
        print("\n Все данные успешно загружены!")
        sys.exit(0)
    else:
        print("\n Ошибка загрузки данных")
        sys.exit(1)