"""Модуль загрузки данных из CSV файлов в базу данных.

Содержит функции для импорта шаблонов растений и достижений из CSV.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Optional
from .db_manager import get_db_manager

logger = logging.getLogger(__name__)


def load_plants_from_csv_raw(csv_path: str, db_path: str = "careforme.db") -> bool:
    """Загружает шаблоны растений из CSV файла в таблицу plant_templates.

    Поддерживает два формата для JSON полей (tips и symptoms):
        - JSON массив: '["tip1", "tip2"]'
        - Разделитель | : 'tip1|tip2'

    :param csv_path: Путь к CSV файлу с растениями
    :type csv_path: str
    :param db_path: Путь к файлу БД (по умолчанию 'careforme.db')
    :type db_path: str
    :return: True если загружено хотя бы одно растение, иначе False
    :rtype: bool

    :raises FileNotFoundError: Если CSV файл не найден

    :example:
        >>> success = load_plants_from_csv_raw("csv/plant_catalog.csv")
        >>> print(success)
        True
    """
    if not Path(csv_path).exists():
        logger.error(f"CSV файл не найден: {csv_path}")
        return False

    db = get_db_manager(db_path)

    try:
        db.execute_update("DELETE FROM plant_templates")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSV пуст")
            return False

        successful = 0
        for i, row in enumerate(rows, start=2):
            try:
                # Парсинг JSON полей
                tips = row.get('tips', '[]')
                if tips and not tips.startswith('['):
                    tips_list = [t.strip() for t in tips.split('|') if t.strip()]
                    tips = json.dumps(tips_list, ensure_ascii=False)
                elif not tips:
                    tips = '[]'

                symptoms = row.get('symptoms', '[]')
                if symptoms and not symptoms.startswith('['):
                    symptoms_list = [s.strip() for s in symptoms.split('|') if s.strip()]
                    symptoms = json.dumps(symptoms_list, ensure_ascii=False)
                elif not symptoms:
                    symptoms = '[]'

                query = """
                    INSERT INTO plant_templates (
                        species_id, species_name, nickname, description,
                        character_trait, water_interval_min, water_interval_max,
                        light_requirement, humidity_preference, watering_advice,
                        light_advice, flowering_conditions, temp_advice,
                        tips, symptoms, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                params = (
                    int(row.get('species_id', 0)),
                    row.get('species_name', '').strip(),
                    row.get('nickname', '').strip(),
                    row.get('description', ''),
                    row.get('character_trait', ''),
                    int(row.get('water_interval_min', 0)),
                    int(row.get('water_interval_max', 0)),
                    row.get('light_requirement', 'medium').lower(),
                    row.get('humidity_preference', 'medium'),
                    row.get('watering_advice', ''),
                    row.get('light_advice', ''),
                    row.get('flowering_conditions', ''),
                    row.get('temp_advice', ''),
                    tips,
                    symptoms,
                    int(row.get('sort_order', 0))
                )

                if db.execute_update(query, params):
                    successful += 1
                    print(f"  ✓ Загружен {row.get('species_name', 'Unknown')}")

            except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                continue

        print(f"Загружено {successful} шаблонов растений")
        return successful > 0

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return False


def load_achievements_from_csv_raw(csv_path: str, db_path: str = "careforme.db") -> bool:
    """Загружает достижения из CSV файла в таблицу achievements.

    :param csv_path: Путь к CSV файлу с достижениями
    :type csv_path: str
    :param db_path: Путь к файлу БД (по умолчанию 'careforme.db')
    :type db_path: str
    :return: True если загружено хотя бы одно достижение, иначе False
    :rtype: bool

    :example:
        >>> success = load_achievements_from_csv_raw("csv/achievements_catalog.csv")
        >>> print(success)
        True
    """
    if not Path(csv_path).exists():
        logger.error(f"CSV файл не найден: {csv_path}")
        return False

    db = get_db_manager(db_path)

    try:
        db.execute_update("DELETE FROM achievements")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSV достижений пуст")
            return False

        successful = 0
        for i, row in enumerate(rows, start=2):
            try:
                is_active = row.get('is_active', 'true').lower() in ['true', '1', 'yes', 'on']

                query = """
                    INSERT INTO achievements (
                        name, description, requirement_type, 
                        target_value, reward_coins, reward_xp, is_active, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

                params = (
                    row.get('name', '').strip(),
                    row.get('description', ''),
                    row.get('requirement_type', '').strip(),
                    int(row.get('target_value', 0)),
                    int(row.get('reward_coins', 50)),
                    int(row.get('reward_xp', 25)),
                    is_active,
                    int(row.get('sort_order', 0))
                )

                if db.execute_update(query, params):
                    successful += 1
                    print(f"  ✓ Загружено достижение: {row.get('name', 'Unknown')}")

            except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                continue

        print(f"Загружено {successful} достижений")
        return successful > 0

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return False


def verify_data(db_path: str = "careforme.db") -> dict:
    """Проверяет количество записей в основных таблицах.

    :param db_path: Путь к файлу БД
    :type db_path: str
    :return: Словарь с количеством записей в таблицах
    :rtype: dict

    :returns::
        {
            'plants_count': 15,
            'achievements_count': 10,
            'users_count': 0
        }

    :example:
        >>> stats = verify_data()
        >>> print(f"Растений в БД: {stats['plants_count']}")
    """
    db = get_db_manager(db_path)

    plants = db.execute_query("SELECT COUNT(*) as count FROM plant_templates")
    achievements = db.execute_query("SELECT COUNT(*) as count FROM achievements")
    users = db.execute_query("SELECT COUNT(*) as count FROM users")

    return {
        'plants_count': plants[0]['count'] if plants else 0,
        'achievements_count': achievements[0]['count'] if achievements else 0,
        'users_count': users[0]['count'] if users else 0
    }


def get_all_plants(db_path: str = "careforme.db") -> list:
    """Получает все шаблоны растений из БД.

    :param db_path: Путь к файлу БД
    :type db_path: str
    :return: Список всех растений, отсортированных по sort_order
    :rtype: list

    :example:
        >>> plants = get_all_plants()
        >>> for p in plants:
        ...     print(p['species_name'])
    """
    db = get_db_manager(db_path)
    return db.execute_query("""
        SELECT species_id, species_name, nickname, description, character_trait,
               water_interval_min, water_interval_max, light_requirement, humidity_preference,
               watering_advice, light_advice, tips, symptoms, sort_order
        FROM plant_templates 
        ORDER BY sort_order
    """)


def get_plant_by_id(species_id: int, db_path: str = "careforme.db") -> Optional[dict]:
    """Получает шаблон растения по species_id.

    :param species_id: ID вида растения
    :type species_id: int
    :param db_path: Путь к файлу БД
    :type db_path: str
    :return: Словарь с данными растения или None
    :rtype: Optional[dict]

    :example:
        >>> plant = get_plant_by_id(1)
        >>> if plant:
        ...     print(plant['species_name'])
    """
    db = get_db_manager(db_path)
    result = db.execute_query(
        "SELECT * FROM plant_templates WHERE species_id = ?",
        (species_id,)
    )
    return result[0] if result else None