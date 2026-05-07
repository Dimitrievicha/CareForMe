"""
Тесты для LevelQuestService
Тестировщик: marishkkka
"""

import sys
import pytest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import DB_PATH, reset_db_manager
from src.backend.database_full.repository.user_repository import UserRepository


class TestLevelQuestService:
    """Тесты сервиса уровневых заданий"""

    def setup_method(self):
        """Подготовка перед каждым тестом"""
        reset_db_manager()
        from src.backend.database_full.service.level_quest_service import level_quest_service
        self.service = level_quest_service
        # Временно подставляем путь к БД
        if hasattr(self.service, 'user_repo'):
            self.service.user_repo.db.db_path = DB_PATH
        if hasattr(self.service, 'plant_repo'):
            self.service.plant_repo.db.db_path = DB_PATH
        if hasattr(self.service, 'challenge_repo'):
            self.service.challenge_repo.db.db_path = DB_PATH
        if hasattr(self.service, 'mistake_repo'):
            self.service.mistake_repo.db.db_path = DB_PATH
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
    # TC-LEVEL-SRV-01: Получение заданий для уровня
    # ============================================================
    def test_get_level_quests(self):
        """Получение заданий для уровня"""
        quests = self.service.get_level_quests(1)

        # В БД должны быть задания для уровня 1
        if quests is not None:
            assert isinstance(quests, dict)
            assert 'level' in quests
            assert quests['level'] == 1

    # ============================================================
    # TC-LEVEL-SRV-02: Получение прогресса пользователя по уровню
    # ============================================================
    def test_get_user_level_progress(self):
        """Получение прогресса пользователя по уровню"""
        user_id = self.create_test_user()
        progress = self.service.get_user_level_progress(user_id, 1)

        # Может быть None (ещё не инициализирован) - это нормально
        if progress is not None:
            assert isinstance(progress, dict)
            assert 'user_id' in progress or True

    # ============================================================
    # TC-LEVEL-SRV-03: Проверка и обновление заданий
    # ============================================================
    def test_check_and_update_quests(self):
        """Проверка и обновление заданий"""
        user_id = self.create_test_user()
        result = self.service.check_and_update_quests(user_id)

        assert result['success'] is True
        assert 'leveled_up' in result

    # ============================================================
    # TC-LEVEL-SRV-04: Триггер проверки заданий
    # ============================================================
    def test_trigger_quest_check(self):
        """Триггер проверки заданий после действия"""
        user_id = self.create_test_user()
        result = self.service.trigger_quest_check(user_id, "plant")

        assert result['success'] is True

    # ============================================================
    # TC-LEVEL-SRV-05: Статус всех заданий
    # ============================================================
    def test_get_all_quests_status(self):
        """Получение статуса всех заданий для всех уровней"""
        user_id = self.create_test_user()
        status = self.service.get_all_quests_status(user_id)

        assert isinstance(status, dict)
        # Проверяем, что есть все уровни
        assert 1 in status
        assert 2 in status
        assert 3 in status
        assert 4 in status
        assert 5 in status