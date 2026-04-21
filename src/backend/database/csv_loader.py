import csv
import json
import logging
from sqlalchemy.orm import Session
from models import PlantTemplate, Challenge
from sqlalchemy import inspect

logger = logging.getLogger(__name__)


def load_plant_templates_from_csv(db: Session, file_path: str) -> bool:
    """Загрузка шаблонов растений из CSV файла"""
    try:
        # Очищаем существующие данные (опционально)
        db.query(PlantTemplate).delete()

        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSV пуст или содержит только заголовок")
            return False

        templates = []
        for i, row in enumerate(rows, start=2):
            try:
                # Парсинг JSON-полей с защитой от ошибок
                tips = []
                if row.get("tips"):
                    try:
                        tips = json.loads(row["tips"])
                    except json.JSONDecodeError:
                        # Если не JSON, разбиваем по |
                        tips = [t.strip() for t in row["tips"].split("|") if t.strip()]

                symptoms = []
                if row.get("symptoms"):
                    try:
                        symptoms = json.loads(row["symptoms"])
                    except json.JSONDecodeError:
                        # Если не JSON, разбиваем по |
                        symptoms = [s.strip() for s in row["symptoms"].split("|") if s.strip()]

                template = PlantTemplate(
                    species_id=int(row.get("species_id", 0)),
                    species_name=row.get("species_name", "").strip(),
                    nickname=row.get("nickname", "").strip(),
                    description=row.get("description", ""),
                    character_trait=row.get("character_trait", ""),
                    water_interval_min=int(row.get("water_interval_min", 0)),
                    water_interval_max=int(row.get("water_interval_max", 0)),
                    light_requirement=row.get("light_requirement", "medium").lower(),
                    humidity_preference=row.get("humidity_preference", "medium"),
                    watering_advice=row.get("watering_advice", ""),
                    light_advice=row.get("light_advice", ""),
                    flowering_conditions=row.get("flowering_conditions", ""),
                    temp_advice=row.get("temp_advice", ""),
                    tips=tips,
                    symptoms=symptoms
                )
                templates.append(template)
                logger.info(f"Подготовлен шаблон: {template.species_name}")

            except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                continue

        if not templates:
            logger.error("Нет валидных шаблонов для загрузки")
            return False

        # Сохраняем все шаблоны
        for template in templates:
            db.add(template)

        db.commit()
        logger.info(f"Загружено {len(templates)} шаблонов растений")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Критическая ошибка загрузки: {e}")
        return False


def load_challenges_from_csv(db: Session, file_path: str) -> bool:
    """Загрузка достижений из CSV файла"""
    try:
        # Очищаем существующие данные
        db.query(Challenge).delete()

        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSV достижений пуст")
            return False

        challenges = []
        for i, row in enumerate(rows, start=2):
            try:
                # Преобразуем строку is_active в булево значение
                is_active = row.get("is_active", "true").lower() in ["true", "1", "yes", "on"]

                challenge = Challenge(
                    name=row.get("name", "").strip(),
                    description=row.get("description", ""),
                    requirement_type=row.get("requirement_type", "").strip(),
                    target_value=int(row.get("target_value", 0)),
                    reward_coins=int(row.get("reward_coins", 50)),
                    is_active=is_active
                )
                challenges.append(challenge)
                logger.info(f"Подготовлено достижение: {challenge.name}")

            except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                continue

        if not challenges:
            logger.error("Нет валидных достижений для загрузки")
            return False

        # Сохраняем все достижения
        for challenge in challenges:
            db.add(challenge)

        db.commit()
        logger.info(f"Загружено {len(challenges)} достижений")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка загрузки достижений: {e}")
        return False


def check_and_create_tables(db: Session):
    """Проверяет и создает таблицы если их нет"""
    from sqlalchemy import text

    inspector = inspect(db.get_bind())
    tables = inspector.get_table_names()

    if not tables:
        logger.info("Таблицы не найдены, создаем...")
        from models import Base
        Base.metadata.create_all(db.get_bind())
        logger.info("Таблицы успешно созданы")
    else:
        logger.info(f"Таблицы уже существуют: {', '.join(tables)}")