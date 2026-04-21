#!/usr/bin/env python3
import logging
import sys
import os
from engine import SessionLocal, engine
from models import Base
from csv_loader import load_plant_templates_from_csv, load_challenges_from_csv, check_and_create_tables

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_database():
    """Инициализация базы данных"""
    try:
        # Создаем таблицы
        logger.info("Создание таблиц...")
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы успешно созданы")
        return True
    except Exception as e:
        logger.error(f"Ошибка создания таблиц: {e}")
        return False


def enable_sqlite_pragmas():
    """Включает оптимальные настройки для SQLite"""
    if os.getenv("DB_TYPE", "sqlite") == "sqlite":
        try:
            with engine.connect() as conn:
                # Включаем WAL-режим (лучше для веб-приложений)
                conn.execute("PRAGMA journal_mode=WAL")
                # Включаем поддержку внешних ключей
                conn.execute("PRAGMA foreign_keys=ON")
                # Увеличиваем кэш
                conn.execute("PRAGMA cache_size=-20000")  # 20MB кэша
                logger.info("✅ SQLite оптимизирован (WAL режим, foreign keys, кэш)")
        except Exception as e:
            logger.warning(f"Не удалось настроить PRAGMA: {e}")


def load_all_data():
    """Загрузка всех данных из CSV"""
    db = SessionLocal()
    try:
        # Загрузка шаблонов растений
        logger.info("Загрузка шаблонов растений...")
        success_plants = load_plant_templates_from_csv(db, "plant_catalog.csv")

        # Загрузка достижений
        logger.info("Загрузка достижений...")
        success_challenges = load_challenges_from_csv(db, "achievements_catalog.csv")

        if success_plants and success_challenges:
            logger.info("✅ Все данные успешно загружены!")
        elif success_plants:
            logger.warning("⚠️ Загружены только шаблоны растений")
        elif success_challenges:
            logger.warning("⚠️ Загружены только достижения")
        else:
            logger.error("❌ Не удалось загрузить данные")
            return False

        return True

    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {e}")
        return False
    finally:
        db.close()


def verify_data():
    """Проверка загруженных данных"""
    db = SessionLocal()
    try:
        from models import PlantTemplate, Challenge

        plants_count = db.query(PlantTemplate).count()
        challenges_count = db.query(Challenge).count()

        logger.info(f"📊 Статистика базы данных:")
        logger.info(f"   - Шаблонов растений: {plants_count}")
        logger.info(f"   - Достижений: {challenges_count}")

        if plants_count > 0:
            logger.info("   - Растения в БД:")
            for plant in db.query(PlantTemplate).all():
                logger.info(f"     • {plant.species_name} (ID: {plant.species_id})")

        if challenges_count > 0:
            logger.info("   - Достижения в БД:")
            for challenge in db.query(Challenge).all():
                logger.info(f"     • {challenge.name} - {challenge.reward_coins} монет")

        return plants_count > 0 and challenges_count > 0

    except Exception as e:
        logger.error(f"Ошибка проверки данных: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("🚀 Начало загрузки данных в базу данных")

    # Явно устанавливаем SQLite (можно закомментировать, если хотите через переменную окружения)
    os.environ["DB_TYPE"] = "sqlite"

    # Инициализация БД
    if not init_database():
        logger.error("Не удалось инициализировать базу данных")
        sys.exit(1)

    # Включаем оптимальные настройки SQLite
    enable_sqlite_pragmas()

    # Загрузка данных
    if not load_all_data():
        logger.error("Не удалось загрузить данные")
        sys.exit(1)

    # Проверка данных
    if verify_data():
        logger.info("✅ Загрузка завершена успешно!")
        logger.info("💾 База данных сохранена в файл: careforme.db")
    else:
        logger.warning("⚠️ Загрузка завершена с предупреждениями")
        sys.exit(1)