"""
Автоматизированные тесты LevelQuestService.

Проверяем:
- получение заданий уровня;
- получение прогресса пользователя;
- инициализацию прогресса;
- расчёт прогресса по заданиям;
- получение статуса всех уровней.

Инструменты:
- pytest
- unittest.mock
"""
import sys
from pathlib import Path
from unittest.mock import Mock

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from backend.database_full.service.level_quest_service import LevelQuestService


def create_service():
    service = LevelQuestService()

    service.user_repo = Mock()
    service.plant_repo = Mock()
    service.challenge_repo = Mock()
    service.mistake_repo = Mock()
    service.db = Mock()

    return service


# =========================
# Получение заданий уровня
# =========================

def test_get_level_quests_found():
    service = create_service()

    service.db.execute_query.return_value = [
        {"level": 1}
    ]

    result = service.get_level_quests(1)

    assert result["level"] == 1


def test_get_level_quests_not_found():
    service = create_service()

    service.db.execute_query.return_value = []

    result = service.get_level_quests(99)

    assert result is None


# =========================
# Получение прогресса уровня
# =========================

def test_get_user_level_progress_found():
    service = create_service()

    service.db.execute_query.return_value = [
        {"level": 1}
    ]

    result = service.get_user_level_progress("user1", 1)

    assert result["level"] == 1


def test_get_user_level_progress_not_found():
    service = create_service()

    service.db.execute_query.return_value = []

    result = service.get_user_level_progress("user1", 1)

    assert result is None


# =========================
# Инициализация прогресса
# =========================

def test_init_user_level_progress_success():
    service = create_service()

    service.db.execute_update.return_value = True

    result = service.init_user_level_progress("user1", 1)

    assert result is True


# =========================
# Проверка прогресса заданий
# =========================

def test_check_quest_completion_without_profile():
    service = create_service()

    service.user_repo.get_profile.return_value = None

    result = service._check_quest_completion(
        "user1",
        "plant_first",
        1
    )

    assert result == 0


def test_check_quest_completion_plant_first_completed():
    service = create_service()

    service.user_repo.get_profile.return_value = {
        "total_plants_grown": 2
    }

    result = service._check_quest_completion(
        "user1",
        "plant_first",
        1
    )

    assert result == 1


def test_check_quest_completion_water_count():
    service = create_service()

    service.user_repo.get_profile.return_value = {
        "total_waterings": 15
    }

    result = service._check_quest_completion(
        "user1",
        "water_count",
        10
    )

    assert result == 15


def test_check_quest_completion_daily_login_streak():
    service = create_service()

    service.user_repo.get_profile.return_value = {
        "consecutive_days": 7
    }

    result = service._check_quest_completion(
        "user1",
        "daily_login_streak",
        5
    )

    assert result == 7


def test_check_quest_completion_unknown_type():
    service = create_service()

    service.user_repo.get_profile.return_value = {}

    result = service._check_quest_completion(
        "user1",
        "unknown",
        1
    )

    assert result == 0
# =========================
# Проверка повышения уровня
# =========================

def test_check_and_update_user_not_found():
    service = create_service()

    service.user_repo.get_profile.return_value = None

    result = service.check_and_update_quests("user1")

    assert result["success"] is False
    assert result["error"] == "Пользователь не найден"


def test_check_and_update_max_level():
    service = create_service()

    service.user_repo.get_profile.return_value = {
        "current_level": 5
    }

    result = service.check_and_update_quests("user1")

    assert result["success"] is True
    assert result["max_level_reached"] is True
    assert result["leveled_up"] is False


def test_check_and_update_level_quests_not_found():
    service = create_service()

    service.user_repo.get_profile.return_value = {
        "current_level": 1
    }

    service.get_level_quests = Mock(return_value=None)

    result = service.check_and_update_quests("user1")

    assert result["success"] is False


# =========================
# Триггер проверки заданий
# =========================

def test_trigger_quest_check():
    service = create_service()

    service.check_and_update_quests = Mock(
        return_value={"success": True}
    )

    result = service.trigger_quest_check(
        "user1",
        "water"
    )

    assert result["success"] is True

    service.check_and_update_quests.assert_called_once_with(
        "user1"
    )


# =========================
# Получение статуса уровней
# =========================

def test_get_all_quests_status():
    service = create_service()

    service.user_repo.get_profile.return_value = {
        "current_level": 2
    }

    service.get_level_quests = Mock(return_value={})
    service.get_user_level_progress = Mock(
        return_value={
            "level_completed": True
        }
    )

    result = service.get_all_quests_status("user1")

    assert len(result) == 5
    assert result[1]["status"] == "completed"


# =========================
# Выдача награды
# =========================

def test_claim_reward_returns_reward():
    service = create_service()

    quests = {
        "reward_type": "new_pot",
        "reward_value": "pot_1",
        "reward_description": "Новый горшок"
    }

    result = service._claim_reward(
        "user1",
        1,
        quests
    )

    assert result["type"] == "new_pot"
    assert result["value"] == "pot_1"
    assert result["description"] == "Новый горшок"