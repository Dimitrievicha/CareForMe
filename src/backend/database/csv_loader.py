import csv
import json
import logging
from sqlalchemy.orm import Session
from models import PlantTemplate, Challenge

logger = logging.getLogger(__name__)

def load_plant_templates_from_csv(db: Session, file_path: str) -> bool:
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if len(rows) <= 1:
            logger.warning("CSV пуст или содержит только заголовок")
            return False

        valid_rows = []
        for i, row in enumerate(rows, start=2):
            try:
                # Парсинг JSON-полей с защитой от ошибок
                tips = json.loads(row.get("tips", "[]")) if row.get("tips") else []
                symptoms = json.loads(row.get("symptoms", "[]")) if row.get("symptoms") else []

                template = PlantTemplate(
                    species_name=row.get("species_name", "").strip(),
                    nickname=row.get("nickname", "").strip(),
                    description=row.get("description", ""),
                    character_trait=row.get("character_trait", ""),
                    water_interval_min=int(row.get("water_interval_min", 0)),
                    water_interval_max=int(row.get("water_interval_max", 0)),
                    light_requirement=row.get("light_requirement", "medium").lower(),
                    watering_advice=row.get("watering_advice", ""),
                    light_advice=row.get("light_advice", ""),
                    flowering_conditions=row.get("flowering_conditions", ""),
                    tips=tips,
                    symptoms=symptoms
                )
                valid_rows.append(template.__dict__)
            except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                continue

        if not valid_rows:
            return False

        # Быстрая вставка (аналог batch в Kotlin)
        db.bulk_insert_mappings(PlantTemplate, valid_rows)
        db.commit()
        logger.info(f"Загружено {len(valid_rows)} шаблонов растений")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Критическая ошибка загрузки: {e}")
        return False

def load_challenges_from_csv(db: Session, file_path: str) -> bool:
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        valid = []
        for i, row in enumerate(rows, start=2):
            try:
                challenge = Challenge(
                    name=row.get("name", "").strip(),
                    description=row.get("description", ""),
                    requirement_type=row.get("requirement_type", "").strip(),
                    target_value=int(row.get("target_value", 0)),
                    reward_coins=int(row.get("reward_coins", 50)),
                    is_active=row.get("is_active", "True").lower() == "true"
                )
                valid.append(challenge.__dict__)
            except Exception as e:
                logger.error(f"Ошибка в строке {i}: {e}")
                continue

        if valid:
            db.bulk_insert_mappings(Challenge, valid)
            db.commit()
            logger.info(f"Загружено {len(valid)} достижений")
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка загрузки достижений: {e}")
        return False