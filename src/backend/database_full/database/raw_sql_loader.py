"""
Модуль загрузки данных из CSV файлов в базу данных.

Содержит функции для импорта:
    - Шаблонов растений из plant_catalog.csv
    - Достижений из achievements_catalog.csv
    - Советов из tips.csv
    - Заданий уровней из level_requirements.csv
    - Дизайнов из designs.csv

"""

import csv
import json
import logging
from pathlib import Path
from typing import Optional

from .db_manager import get_db_manager

# Настройка логирования
logger = logging.getLogger(__name__)


def load_plants_from_csv_raw(csv_path: str, db_path: str = "careforme.db") -> bool:
    """
    Загружает шаблоны растений из CSV файла в таблицу plant_templates.

    Поддерживает два формата для JSON полей (tips и symptoms):
        - JSON массив: '["tip1", "tip2"]'
        - Разделитель | : 'tip1|tip2'

    Args:
        csv_path: Путь к CSV файлу с растениями
        db_path: Путь к файлу БД (по умолчанию 'careforme.db')

    Returns:
        True если загружено хотя бы одно растение, иначе False

    Raises:
        FileNotFoundError: Если CSV файл не найден (логируется ошибка)


    Ожидаемая структура CSV:
        species_id,species_name,nickname,description,character_trait,
        water_interval_min,water_interval_max,light_requirement,humidity_preference,
        watering_advice,light_advice,flowering_conditions,temp_advice,tips,symptoms,sort_order
    """
    if not Path(csv_path).exists():
        logger.error(f"CSV файл не найден: {csv_path}")
        return False

    db = get_db_manager(db_path)

    try:
        db.execute_update("DELETE FROM plant_templates")
        logger.info("Таблица plant_templates очищена")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSV файл пуст")
            return False

        successful = 0

        for i, row in enumerate(rows, start=2):
            try:
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
                logger.error(f"Данные строки: {row}")
                continue

        print(f"Загружено {successful} шаблонов растений")
        logger.info(f"Загружено {successful} шаблонов растений из {csv_path}")
        return successful > 0

    except Exception as e:
        logger.error(f"Критическая ошибка при загрузке растений: {e}")
        return False


def load_achievements_from_csv_raw(csv_path: str, db_path: str = "careforme.db") -> bool:
    """
    Загружает достижения из CSV файла в таблицу achievements.

    Достижения НЕ дают монет и XP, только эмоциональную ценность.

    Args:
        csv_path: Путь к CSV файлу с достижениями
        db_path: Путь к файлу БД (по умолчанию 'careforme.db')

    Returns:
        True если загружено хотя бы одно достижение, иначе False


    Ожидаемая структура CSV:
        name,description,requirement_type,target_value,is_active,sort_order
    """
    if not Path(csv_path).exists():
        logger.error(f"CSV файл не найден: {csv_path}")
        return False

    db = get_db_manager(db_path)

    try:
        db.execute_update("DELETE FROM achievements")
        logger.info("Таблица achievements очищена")

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
                        target_value, is_active, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """

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
                continue

        print(f"Загружено {successful} достижений")
        logger.info(f"Загружено {successful} достижений из {csv_path}")
        return successful > 0

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return False


def load_tips_from_csv_raw(csv_path: str, db_path: str = "careforme.db") -> bool:
    """
    Загружает советы из CSV файла в таблицу tips.

    Args:
        csv_path: Путь к CSV файлу с советами
        db_path: Путь к файлу БД (по умолчанию 'careforme.db')

    Returns:
        True если загружено хотя бы один совет, иначе False

    Ожидаемая структура CSV:
        tip_type,title,message,is_positive
    """
    if not Path(csv_path).exists():
        logger.error(f"CSV файл не найден: {csv_path}")
        return False

    db = get_db_manager(db_path)

    try:
        db.execute_update("DELETE FROM tips")
        logger.info("Таблица tips очищена")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSV советов пуст")
            return False

        successful = 0

        for i, row in enumerate(rows, start=2):
            try:
                is_positive = row.get('is_positive', '0').lower() in ['true', '1', 'yes', 'on']

                query = """
                    INSERT INTO tips (
                        tip_type, title, message, is_positive
                    ) VALUES (?, ?, ?, ?)
                """

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
                continue

        print(f"Загружено {successful} советов")
        logger.info(f"Загружено {successful} советов из {csv_path}")
        return successful > 0

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return False


def load_level_requirements_from_csv_raw(csv_path: str, db_path: str = "careforme.db") -> bool:
    """
    Загружает задания уровней из CSV файла в таблицу level_requirements.

    Args:
        csv_path: Путь к CSV файлу с заданиями уровней
        db_path: Путь к файлу БД (по умолчанию 'careforme.db')

    Returns:
        True если загружено хотя бы одно задание уровня, иначе False

    Ожидаемая структура CSV:
        level,quest1_type,quest1_target,quest1_description,quest2_type,quest2_target,
        quest2_description,quest3_type,quest3_target,quest3_description,
        reward_type,reward_value,reward_description
    """
    if not Path(csv_path).exists():
        logger.error(f"CSV файл не найден: {csv_path}")
        return False

    db = get_db_manager(db_path)

    try:
        db.execute_update("DELETE FROM level_requirements")
        logger.info("Таблица level_requirements очищена")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSV заданий уровней пуст")
            return False

        successful = 0

        for i, row in enumerate(rows, start=2):
            try:
                # Обработка пустых значений для quest3
                quest3_type = row.get('quest3_type', '').strip()
                quest3_target = row.get('quest3_target', '')
                quest3_description = row.get('quest3_description', '').strip()

                query = """
                    INSERT INTO level_requirements (
                        level, quest1_type, quest1_target, quest1_description,
                        quest2_type, quest2_target, quest2_description,
                        quest3_type, quest3_target, quest3_description,
                        reward_type, reward_value, reward_description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                params = (
                    int(row.get('level', 0)),
                    row.get('quest1_type', '').strip() or None,
                    int(row.get('quest1_target', 0)) if row.get('quest1_target', '').strip() else None,
                    row.get('quest1_description', '').strip() or None,
                    row.get('quest2_type', '').strip() or None,
                    int(row.get('quest2_target', 0)) if row.get('quest2_target', '').strip() else None,
                    row.get('quest2_description', '').strip() or None,
                    quest3_type or None,
                    int(quest3_target) if quest3_target and quest3_target.strip() else None,
                    quest3_description or None,
                    row.get('reward_type', '').strip() or None,
                    row.get('reward_value', '').strip() or None,
                    row.get('reward_description', '').strip() or None
                )

                if db.execute_update(query, params):
                    successful += 1
                    print(f"  ✓ Загружен уровень {row.get('level', 'Unknown')}")

            except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                logger.error(f"Данные строки: {row}")
                continue

        print(f"Загружено {successful} уровней")
        logger.info(f"Загружено {successful} уровней из {csv_path}")
        return successful > 0

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return False


def load_designs_from_csv_raw(csv_path: str, db_path: str = "careforme.db") -> bool:
    """
    Загружает дизайны из CSV файла в таблицу designs.

    Args:
        csv_path: Путь к CSV файлу с дизайнами
        db_path: Путь к файлу БД (по умолчанию 'careforme.db')

    Returns:
        True если загружено хотя бы один дизайн, иначе False

    Ожидаемая структура CSV:
        design_type,design_id,name,description,image_path,is_default,sort_order
    """
    if not Path(csv_path).exists():
        logger.warning(f"CSV файл дизайнов не найден: {csv_path}, пропускаем")
        return False

    db = get_db_manager(db_path)

    try:
        db.execute_update("DELETE FROM designs")
        logger.info("Таблица designs очищена")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSV дизайнов пуст")
            return False

        successful = 0

        for i, row in enumerate(rows, start=2):
            try:
                is_default = row.get('is_default', '0').lower() in ['true', '1', 'yes', 'on']

                query = """
                    INSERT INTO designs (
                        design_type, design_id, name, description, 
                        image_path, is_default, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """

                params = (
                    row.get('design_type', '').strip(),
                    row.get('design_id', '').strip(),
                    row.get('name', '').strip(),
                    row.get('description', ''),
                    row.get('image_path', '').strip() or None,
                    is_default,
                    int(row.get('sort_order', 0))
                )

                if db.execute_update(query, params):
                    successful += 1
                    print(f"  ✓ Загружен дизайн: {row.get('name', 'Unknown')}")

            except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                continue

        print(f"Загружено {successful} дизайнов")
        logger.info(f"Загружено {successful} дизайнов из {csv_path}")
        return successful > 0

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return False


def verify_data(db_path: str = "careforme.db") -> dict:
    """
    Проверяет количество записей в основных таблицах.

    Используется для отладки и проверки корректности загрузки данных.

    Args:
        db_path: Путь к файлу БД

    Returns:
        Словарь с количеством записей в таблицах
    """
    db = get_db_manager(db_path)

    plants = db.execute_query("SELECT COUNT(*) as count FROM plant_templates")
    achievements = db.execute_query("SELECT COUNT(*) as count FROM achievements")
    level_quests = db.execute_query("SELECT COUNT(*) as count FROM level_requirements")
    users = db.execute_query("SELECT COUNT(*) as count FROM users")
    tips = db.execute_query("SELECT COUNT(*) as count FROM tips")
    designs = db.execute_query("SELECT COUNT(*) as count FROM designs")

    result = {
        'plants_count': plants[0]['count'] if plants else 0,
        'achievements_count': achievements[0]['count'] if achievements else 0,
        'level_quests_count': level_quests[0]['count'] if level_quests else 0,
        'users_count': users[0]['count'] if users else 0,
        'tips_count': tips[0]['count'] if tips else 0,
        'designs_count': designs[0]['count'] if designs else 0
    }

    logger.info(f"Статистика БД: {result}")
    return result


def get_all_plants(db_path: str = "careforme.db") -> list:
    """
    Получает все шаблоны растений из БД.

    Args:
        db_path: Путь к файлу БД

    Returns:
        Список всех растений, отсортированных по sort_order
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
    """
    Получает шаблон растения по species_id.

    Args:
        species_id: ID вида растения (1=Спатифиллюм, 2=Кактус, 3=Фикус)
        db_path: Путь к файлу БД

    Returns:
        Словарь с данными растения или None
    """
    db = get_db_manager(db_path)
    result = db.execute_query(
        "SELECT * FROM plant_templates WHERE species_id = ?",
        (species_id,)
    )
    return result[0] if result else None