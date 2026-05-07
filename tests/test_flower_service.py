"""
Тесты для FlowerService
Тестировщик: marishkkka
"""

import sys
import pytest
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH, reset_db_manager
from src.backend.database_full.service.flower_service import FlowerService


class TestFlowerService:
    """Тесты сервиса управления растениями"""

    def setup_method(self):
        """Перед каждым тестом сбрасываем синглтон и создаём свежий сервис"""
        reset_db_manager()
        self.service = FlowerService()
        # Убедимся, что сервис создан с правильным путём
        self.service.plant_repo.db.db_path = DB_PATH

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-01 - Посадка растения
    # ============================================================
    def test_tc_flower_01_plant_flower_success(self):
        """Посадка растения при наличии свободного слота"""
        # Сначала создадим пользователя в БД
        import uuid
        user_id = str(uuid.uuid4())
        from src.backend.database_full.repository.user_repository import UserRepository
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, "testuser", "hash123")
        user_repo.create_profile(user_id, "Test User")

        # Сажаем растение
        result = self.service.plant_flower(user_id, species_id=1, custom_name="Мой цветочек")

        assert result["success"] is True
        assert "plant_id" in result
        assert result["species_id"] == 1

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-02 - Посадка при отсутствии пользователя
    # ============================================================
    def test_tc_flower_02_plant_flower_user_not_found(self):
        """Попытка посадки для несуществующего пользователя"""
        result = self.service.plant_flower("non-existent-user", species_id=1)

        assert result["success"] is False
        assert "Пользователь не найден" in result["error"]

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-03 - Посадка с неверным species_id
    # ============================================================
    def test_tc_flower_03_plant_flower_invalid_species(self):
        """Попытка посадки с несуществующим species_id"""
        import uuid
        user_id = str(uuid.uuid4())
        from src.backend.database_full.repository.user_repository import UserRepository
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, "testuser2", "hash123")
        user_repo.create_profile(user_id, "Test User 2")

        result = self.service.plant_flower(user_id, species_id=999)

        assert result["success"] is False
        assert "Растение не найдено" in result["error"]

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-04 - Получение сада пользователя
    # ============================================================
    def test_tc_flower_04_get_my_garden(self):
        """Получение списка растений пользователя"""
        import uuid
        user_id = str(uuid.uuid4())
        from src.backend.database_full.repository.user_repository import UserRepository
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, "testuser3", "hash123")
        user_repo.create_profile(user_id, "Test User 3")

        # Сажаем растение
        self.service.plant_flower(user_id, species_id=1)

        garden = self.service.get_my_garden(user_id)

        assert isinstance(garden, list)
        assert len(garden) > 0

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-05 - Получение деталей растения
    # ============================================================
    def test_tc_flower_05_get_plant_details(self):
        """Получение детальной информации о растении"""
        import uuid
        user_id = str(uuid.uuid4())
        from src.backend.database_full.repository.user_repository import UserRepository
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, "testuser4", "hash123")
        user_repo.create_profile(user_id, "Test User 4")

        result = self.service.plant_flower(user_id, species_id=1)
        plant_id = result["plant_id"]

        details = self.service.get_plant_details(plant_id, user_id)

        assert details is not None
        assert details["id"] == plant_id

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-06 - Доступ к чужому растению
    # ============================================================
    def test_tc_flower_06_get_plant_details_wrong_user(self):
        """Доступ к растению другого пользователя"""
        import uuid
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        from src.backend.database_full.repository.user_repository import UserRepository
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user1_id, "testuser5", "hash123")
        user_repo.create_profile(user1_id, "Test User 5")
        user_repo.create_user(user2_id, "testuser6", "hash123")
        user_repo.create_profile(user2_id, "Test User 6")

        result = self.service.plant_flower(user1_id, species_id=1)
        plant_id = result["plant_id"]

        details = self.service.get_plant_details(plant_id, user2_id)

        assert details is None

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-07 - Полив растения
    # ============================================================
    def test_tc_flower_07_water_flower_success(self):
        """Успешный полив растения"""
        import uuid
        user_id = str(uuid.uuid4())
        from src.backend.database_full.repository.user_repository import UserRepository
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, "testuser7", "hash123")
        user_repo.create_profile(user_id, "Test User 7")

        result = self.service.plant_flower(user_id, species_id=1, custom_name="Кактус")
        plant_id = result["plant_id"]

        water_result = self.service.water_flower(plant_id, user_id)

        assert water_result["success"] is True
        assert "полит" in water_result["message"].lower()

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-08 - Полив несуществующего растения
    # ============================================================
    def test_tc_flower_08_water_flower_not_found(self):
        """Полив несуществующего растения"""
        result = self.service.water_flower("non-existent-plant-id", "some-user")

        assert result["success"] is False
        assert "Растение не найдено" in result["error"]

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-09 - Проверка здоровья растения
    # ============================================================
    def test_tc_flower_09_check_health(self):
        """Проверка здоровья живого растения"""
        import uuid
        user_id = str(uuid.uuid4())
        from src.backend.database_full.repository.user_repository import UserRepository
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, "testuser8", "hash123")
        user_repo.create_profile(user_id, "Test User 8")

        result = self.service.plant_flower(user_id, species_id=1)
        plant_id = result["plant_id"]

        health = self.service.check_health(plant_id, user_id)

        assert health["success"] is True
        assert "health_status" in health
        assert health["is_alive"] if "is_alive" in health else True

    # ============================================================
    # ТЕСТ-КЕЙС: TC-FLOWER-10 - Статистика по стадиям роста
    # ============================================================
    def test_tc_flower_10_get_all_growth_stages(self):
        """Получение статистики по стадиям роста"""
        import uuid
        user_id = str(uuid.uuid4())
        from src.backend.database_full.repository.user_repository import UserRepository
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, "testuser9", "hash123")
        user_repo.create_profile(user_id, "Test User 9")

        self.service.plant_flower(user_id, species_id=1)

        stages = self.service.get_all_growth_stages(user_id)

        assert isinstance(stages, dict)
        assert "seed" in stages
        assert "seedling" in stages
        assert "growing" in stages
        assert "mature" in stages
        assert "flowering" in stages