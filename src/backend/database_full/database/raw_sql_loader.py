"""
Модуль загрузки данных из CSV файлов в базу данных.

Содержит функции для импорта:
    - Шаблонов растений из plant_catalog.csv
    - Достижений из achievements_catalog.csv
    - Советов из tips.csv
    - Заданий уровней из level_requirements.csv

"""

import csv
import logging
from pathlib import Path
from typing import List, Dict

from .db_manager import get_db_manager

# Настройка логирования
logger = logging.getLogger(__name__)

def _read_csv(csv_path: str) -> List[Dict]:
    """
    Читает CSV файл и возвращает список строк как словарей.
    Возвращает [] если файл не найден или пуст.
    """
    path = Path(csv_path)
    if not path.exists():
        logger.error(f"CSV файл не найден: {csv_path}")
        return []
 
    with open(path, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
 
    if not rows:
        logger.warning(f"CSV файл пуст: {csv_path}")
 
    return rows

def load_plants_from_csv_raw(csv_path: str) -> bool:
    """
    Загружает шаблоны растений из CSV файла в таблицу plant_templates.
    """
    rows = _read_csv(csv_path)
    if not rows:
        return False

    db = get_db_manager()
    db.execute_update("DELETE FROM plant_templates")
    query = """
        INSERT INTO plant_templates (
            species_id, species_name, nickname, description, character_trait,
            disease, why_disease,
            water_interval_min, water_interval_max,
            light_requirement, humidity_preference,
            watering_advice, light_advice, tips, symptoms, flowering_conditions,
            unlock_level, sort_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    successful = 0

    for i, row in enumerate(rows, start=2):
        try:
            params = (
                int(row.get('species_id', 0)),
                row.get('species_name', '').strip(),
                row.get('nickname', '').strip(),
                row.get('description', '').strip(),
                row.get('character_trait', '').strip(),
                row.get('disease', '').strip(),
                row.get('why_disease', '').strip(),
                int(row.get('water_interval_min', 0)),
                int(row.get('water_interval_max', 0)),
                row.get('light_requirement', 'medium').lower(),
                row.get('humidity_preference', 'medium').strip(),
                row.get('watering_advice', '').strip(),
                row.get('light_advice', '').strip(),
                row.get('tips', '').strip(),
                row.get('symptoms', '').strip(),
                row.get('flowering_conditions', '').strip(),
                int(row.get('unlock_level', 1)),
                int(row.get('sort_order', 0))
            )

            if db.execute_update(query, params):
                successful += 1
                print(f"  ✓ Загружен {row.get('species_name', 'Unknown')}")

        except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                logger.error(f"Данные строки: {row}")
                continue

    print(f"Загружено {successful} шаблонов растений")
    logger.info(f"Загружено {successful} шаблонов растений из {csv_path}")
    return successful > 0



def load_achievements_from_csv_raw(csv_path: str) -> bool:
    """
    Загружает достижения из CSV файла в таблицу achievements.

    Достижения НЕ дают монет и XP, только эмоциональную ценность.

    Args:
        csv_path: Путь к CSV файлу с достижениями

    Returns:
        True если загружено хотя бы одно достижение, иначе False


    Ожидаемая структура CSV:
        name,description,requirement_type,target_value,is_active,sort_order
    """
    rows = _read_csv(csv_path)
    if not rows:
        return False

    db = get_db_manager()
    db.execute_update("DELETE FROM achievements")

    query = """
        INSERT INTO achievements (
            name, description, requirement_type, 
            target_value, is_active, sort_order
        ) VALUES (?, ?, ?, ?, ?, ?)
        """

    successful = 0

    for i, row in enumerate(rows, start=2):
        try:
            is_active = row.get('is_active', 'true').lower() in ('true', '1', 'yes', 'on')
            params = (
                row.get('name', '').strip(),
                row.get('description', ''),
                row.get('requirement_type', '').strip(),
                int(row.get('target_value', 0)),
                is_active,
                int(row.get('sort_order', 0))
            )

            if db.execute_update(query, params):
                successful += 1
                print(f"  ✓ Загружено достижение: {row.get('name', 'Unknown')}")

        except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")

    print(f"Загружено {successful} достижений")
    logger.info(f"Загружено {successful} достижений из {csv_path}")
    return successful > 0



def load_tips_from_csv_raw(csv_path: str) -> bool:
    """
    Загружает советы из CSV файла в таблицу tips.

    Args:
        csv_path: Путь к CSV файлу с советами

    Returns:
        True если загружено хотя бы один совет, иначе False

    Ожидаемая структура CSV:
        tip_type,title,message,is_positive
    """
    rows = _read_csv(csv_path)
    if not rows:
        return False

    db = get_db_manager()
    db.execute_update("DELETE FROM tips")

    query = """
        INSERT INTO tips (
            tip_type, title, message, is_positive
        ) VALUES (?, ?, ?, ?)
        """

    successful = 0

    for i, row in enumerate(rows, start=2):
        try:
            is_positive = row.get('is_positive', '0').lower() in ['true', '1', 'yes', 'on']

            params = (
                row.get('tip_type', '').strip(),
                row.get('title', '').strip(),
                row.get('message', '').strip(),
                is_positive
            )

            if db.execute_update(query, params):
                successful += 1
                print(f"  ✓ Загружен совет: {row.get('title', row.get('tip_type', 'Unknown'))}")

        except Exception as e:
            logger.error(f"Ошибка в строке {i}: {e}")

    print(f"Загружено {successful} советов")
    logger.info(f"Загружено {successful} советов из {csv_path}")
    return successful > 0

    


def load_level_requirements_from_csv_raw(csv_path: str) -> bool:
    """
    Загружает задания уровней из CSV файла в таблицу level_requirements.

    Args:
        csv_path: Путь к CSV файлу с заданиями уровней

    Returns:
        True если загружено хотя бы одно задание уровня, иначе False

    Ожидаемая структура CSV:
        level,quest1_type,quest1_target,quest1_description,quest2_type,quest2_target,
        quest2_description,quest3_type,quest3_target,quest3_description,
        reward_type,reward_value,reward_description
    """
    rows = _read_csv(csv_path)
    if not rows:
        return False

    db = get_db_manager()
    db.execute_update("DELETE FROM level_requirements")

    query = """
        INSERT INTO level_requirements (
            level, quest1_type, quest1_target, quest1_description,
            quest2_type, quest2_target, quest2_description,
            quest3_type, quest3_target, quest3_description,
            reward_type, reward_value, reward_description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
    
    def int_or_none(value: str):
        """Преобразует строку в int или возвращает None если пусто."""
        v = value.strip() if value else ''
        return int(v) if v else None

    def str_or_none(value: str):
        """Возвращает строку или None если пусто."""
        v = value.strip() if value else ''
        return v or None
    
    successful = 0

    for i, row in enumerate(rows, start=2):
        try:
            params = (
                int(row.get('level', 0)),
                str_or_none(row.get('quest1_type', '')),
                int_or_none(row.get('quest1_target', 0)),
                str_or_none(row.get('quest1_description', '')),

                str_or_none(row.get('quest2_type', '')),
                int_or_none(row.get('quest2_target', 0)),
                str_or_none(row.get('quest2_description', '')),

                str_or_none(row.get('quest3_type', '')),
                int_or_none(row.get("quest3_target", '')),
                str_or_none(row.get("quest3_description", '')),

                str_or_none(row.get('reward_type', '')),
                str_or_none(row.get('reward_value', '')),
                str_or_none(row.get('reward_description', '')),
            )

            if db.execute_update(query, params):
                successful += 1
                print(f"  ✓ Загружен уровень {row.get('level', 'Unknown')}")

        except Exception as e:
            logger.error(f"Ошибка в строке {i}: {e}")
            logger.error(f"Данные строки: {row}")

    print(f"Загружено {successful} уровней")
    logger.info(f"Загружено {successful} уровней из {csv_path}")
    return successful > 0


def verify_data() -> dict:
    """
    Проверяет количество записей в основных таблицах.

    Используется для отладки и проверки корректности загрузки данных.

    Args:
        db_path: Путь к файлу БД

    Returns:
        Словарь с количеством записей в таблицах
    """
    db = get_db_manager()
    tables = {
        'plants_count': 'plant_templates',
        'achievements_count': 'achievements',
        'level_quests_count': 'level_requirements',
        'users_count': 'users',
        'tips_count': 'tips',
    }
    result = {}
    for key, table in tables.items():
        rows = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
        result[key] = rows[0]['count'] if rows else 0

    logger.info(f"Статистика БД: {result}")
    return result

