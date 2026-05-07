"""
Тесты для UserService
Тестировщик: marishkkka
"""

import sys
import pytest
import uuid
import json
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH, reset_db_manager
from src.backend.database_full.repository.user_repository import UserRepository


class TestUserService:
    """Тесты сервиса пользователей"""

    def setup_method(self):
        """Подготовка перед каждым тестом"""
        reset_db_manager()
        # После исправления разработчика:
        # from src.backend.database_full.service.user_service import UserService
        # self.service = UserService(db_path=DB_PATH)
        from src.backend.database_full.service.user_service import user_service
        self.service = user_service
        # Временно подставляем путь
        if hasattr(self.service, 'user_repo'):
            self.service.user_repo.db.db_path = DB_PATH
        if hasattr(self.service, 'db'):
            self.service.db.db_path = DB_PATH

    def create_test_user(self):
        """Создаёт тестового пользователя"""
        user_id = str(uuid.uuid4())
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, f"user_{user_id[:8]}", "hash123")
        user_repo.create_profile(user_id, f"Test User {user_id[:8]}")
        return user_id

    # ============================================================
    # TC-USER-SRV-01: Получение профиля
    # ============================================================
    def test_get_profile_success(self):
        """Успешное получение профиля существующего пользователя"""
        user_id = self.create_test_user()
        profile = self.service.get_profile(user_id)

        assert profile is not None
        assert profile['user_id'] == user_id
        assert 'current_level' in profile

    # ============================================================
    # TC-USER-SRV-02: Получение профиля несуществующего пользователя
    # ============================================================
    def test_get_profile_not_found(self):
        """Получение профиля несуществующего пользователя"""
        profile = self.service.get_profile("non-existent-user")
        assert profile is None

    # ============================================================
    # TC-USER-SRV-03: Получение статистики
    # ============================================================
    def test_get_stats_success(self):
        """Успешное получение статистики"""
        user_id = self.create_test_user()
        stats = self.service.get_stats(user_id)

        assert isinstance(stats, dict)
        assert 'level' in stats
        assert 'max_plants_slots' in stats
        assert 'current_plants' in stats
        assert 'total_plants_grown' in stats
        assert 'total_waterings' in stats
        assert 'consecutive_days' in stats
        assert 'best_streak' in stats

    # ============================================================
    # TC-USER-SRV-04: Получение статистики для несуществующего пользователя
    # ============================================================
    def test_get_stats_default(self):
        """Получение статистики для несуществующего пользователя (дефолтные значения)"""
        stats = self.service.get_stats("non-existent-user")

        assert stats['level'] == 1
        assert stats['max_plants_slots'] == 1
        assert stats['current_plants'] == 0

    # ============================================================
    # TC-USER-SRV-05: Получение текущего уровня
    # ============================================================
    def test_get_current_level(self):
        """Получение текущего уровня пользователя"""
        user_id = self.create_test_user()
        level = self.service.get_current_level(user_id)

        assert isinstance(level, int)
        assert level >= 1

    # ============================================================
    # TC-USER-SRV-06: Получение информации об уровне
    # ============================================================
    def test_get_level_info(self):
        """Получение информации об уровне"""
        user_id = self.create_test_user()
        level_info = self.service.get_level_info(user_id)

        assert 'current_level' in level_info
        assert 'max_level' in level_info

    # ============================================================
    # TC-USER-SRV-07: Обновление ежедневной серии
    # ============================================================
    def test_update_daily_streak(self):
        """Обновление ежедневной серии"""
        user_id = self.create_test_user()
        result = self.service.update_daily_streak(user_id)

        assert result['success'] is True
        assert 'consecutive_days' in result
        assert 'best_streak' in result

    # ============================================================
    # TC-USER-SRV-08: Получение информации о слотах
    # ============================================================
    def test_get_plant_slots(self):
        """Получение информации о слотах для растений"""
        user_id = self.create_test_user()
        slots = self.service.get_plant_slots(user_id)

        assert 'current' in slots
        assert 'max' in slots
        assert 'available' in slots
        assert slots['available'] >= 0

    # ============================================================
    # TC-USER-SRV-09: Проверка свободного слота
    # ============================================================
    def test_has_free_slot(self):
        """Проверка наличия свободного слота"""
        user_id = self.create_test_user()
        has_free = self.service.has_free_slot(user_id)

        assert isinstance(has_free, bool)

    # ============================================================
    # TC-USER-SRV-10: Получение открытых горшков
    # ============================================================
    def test_get_unlocked_pots(self):
        """Получение списка открытых горшков"""
        user_id = self.create_test_user()
        pots = self.service.get_unlocked_pots(user_id)

        assert isinstance(pots, list)
        assert "standard" in pots

    # ============================================================
    # TC-USER-SRV-11: Получение открытых леек
    # ============================================================
    def test_get_unlocked_watering_cans(self):
        """Получение списка открытых леек"""
        user_id = self.create_test_user()
        cans = self.service.get_unlocked_watering_cans(user_id)

        assert isinstance(cans, list)
        assert "standard" in cans

    # ============================================================
    # TC-USER-SRV-12: Получение текущих дизайнов
    # ============================================================
    def test_get_current_designs(self):
        """Получение текущих выбранных дизайнов"""
        user_id = self.create_test_user()
        designs = self.service.get_current_designs(user_id)

        assert 'pot' in designs
        assert 'watering_can' in designs