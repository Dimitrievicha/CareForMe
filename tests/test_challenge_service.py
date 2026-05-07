"""
Тесты для ChallengeService
Тестировщик: marishkkka
"""

import sys
import pytest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH, reset_db_manager
from src.backend.database_full.repository.user_repository import UserRepository


class TestChallengeService:
    """Тесты сервиса достижений"""

    def setup_method(self):
        """Подготовка перед каждым тестом"""
        reset_db_manager()
        from src.backend.database_full.service.challenge_service import challenge_service
        self.service = challenge_service
        # Временно подставляем путь
        if hasattr(self.service, 'challenge_repo'):
            self.service.challenge_repo.db.db_path = DB_PATH
        if hasattr(self.service, 'mistake_repo'):
            self.service.mistake_repo.db.db_path = DB_PATH
        if hasattr(self.service, 'user_repo'):
            self.service.user_repo.db.db_path = DB_PATH
        if hasattr(self.service, 'plant_repo'):
            self.service.plant_repo.db.db_path = DB_PATH

    def create_test_user(self):
        """Создаёт тестового пользователя"""
        user_id = str(uuid.uuid4())
        user_repo = UserRepository(db_path=DB_PATH)
        user_repo.create_user(user_id, f"user_{user_id[:8]}", "hash123")
        user_repo.create_profile(user_id, f"Test User {user_id[:8]}")
        return user_id

    # ============================================================
    # TC-CHAL-SRV-01: Получение всех достижений
    # ============================================================
    def test_get_achievements(self):
        """Получение всех достижений с прогрессом пользователя"""
        user_id = self.create_test_user()
        achievements = self.service.get_achievements(user_id)

        assert isinstance(achievements, list)
        if len(achievements) > 0:
            first = achievements[0]
            assert 'id' in first
            assert 'name' in first
            assert 'current_progress' in first
            assert 'is_completed' in first

    # ============================================================
    # TC-CHAL-SRV-02: Получение выполненных достижений
    # ============================================================
    def test_get_completed(self):
        """Получение выполненных достижений"""
        user_id = self.create_test_user()
        completed = self.service.get_completed(user_id)

        assert isinstance(completed, list)

    # ============================================================
    # TC-CHAL-SRV-03: Количество выполненных достижений
    # ============================================================
    def test_get_completed_count(self):
        """Получение количества выполненных достижений"""
        user_id = self.create_test_user()
        count = self.service.get_completed_count(user_id)

        assert isinstance(count, int)
        assert count >= 0

    # ============================================================
    # TC-CHAL-SRV-04: Запись ошибки
    # ============================================================
    def test_record_mistake(self):
        """Запись ошибки пользователя"""
        user_id = self.create_test_user()
        result = self.service.record_mistake(user_id, "plant_id", "overwater")

        assert result['success'] is True
        assert result['mistake_type'] == "overwater"
        assert 'new_achievements' in result

    # ============================================================
    # TC-CHAL-SRV-05: Статистика по достижениям
    # ============================================================
    def test_get_statistics(self):
        """Получение статистики по достижениям"""
        user_id = self.create_test_user()
        stats = self.service.get_statistics(user_id)

        assert isinstance(stats, dict)
        assert 'plants_grown_to_maturity_perfect' in stats
        assert 'death_count' in stats
        assert 'mistake_count' in stats
        assert 'species_collected' in stats
        assert 'consecutive_days' in stats
        assert 'level' in stats
        assert 'total_achievements' in stats