"""
Автоматизированные тесты LevelQuestService.

Проверяем:
- получение заданий уровня;
- получение прогресса пользователя;
- инициализацию прогресса;
- расчёт прогресса по заданиям;
- повышение уровня;
- выдачу наград;
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


def test_get_level_quests_found():
    service = create_service()
    service.db.execute_query.return_value = [{"level": 1}]
    result = service.get_level_quests(1)
    assert result["level"] == 1


def test_get_level_quests_not_found():
    service = create_service()
    service.db.execute_query.return_value = []
    result = service.get_level_quests(99)
    assert result is None


def test_get_user_level_progress_found():
    service = create_service()
    service.db.execute_query.return_value = [{"level": 1}]
    result = service.get_user_level_progress("user1", 1)
    assert result["level"] == 1


def test_get_user_level_progress_not_found():
    service = create_service()
    service.db.execute_query.return_value = []
    result = service.get_user_level_progress("user1", 1)
    assert result is None


def test_init_user_level_progress_success():
    service = create_service()
    service.db.execute_update.return_value = True
    result = service.init_user_level_progress("user1", 1)
    assert result is True


def test_check_quest_completion_without_profile():
    service = create_service()
    service.user_repo.get_profile.return_value = None
    result = service._check_quest_completion("user1", "plant_first", 1)
    assert result == 0


def test_check_quest_completion_plant_first_completed():
    service = create_service()
    service.user_repo.get_profile.return_value = {"total_plants_grown": 2}
    result = service._check_quest_completion("user1", "plant_first", 1)
    assert result == 1


def test_check_quest_completion_water_count():
    service = create_service()
    service.user_repo.get_profile.return_value = {"total_waterings": 15}
    result = service._check_quest_completion("user1", "water_count", 10)
    assert result == 15


def test_check_quest_completion_daily_login_streak():
    service = create_service()
    service.user_repo.get_profile.return_value = {"consecutive_days": 7}
    result = service._check_quest_completion("user1", "daily_login_streak", 5)
    assert result == 7


def test_check_quest_completion_unknown_type():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 1}
    result = service._check_quest_completion("user1", "unknown", 1)
    assert result == 0


def test_check_quest_completion_grow_to_stage_2():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 1}
    service.plant_repo.get_plants_by_stage.side_effect = [
        [{"id": 1}],
        [{"id": 2}],
        [],
        []
    ]
    result = service._check_quest_completion("user1", "grow_to_stage_2", 2)
    assert result == 2


def test_check_quest_completion_grow_all_species():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 1}
    service.challenge_repo.check_species_collected.return_value = 3
    result = service._check_quest_completion("user1", "grow_all_species", 3)
    assert result == 3


def test_check_quest_completion_achievements_count():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 1}
    service.challenge_repo.get_completed_achievements.return_value = [
        {"id": 1},
        {"id": 2}
    ]
    result = service._check_quest_completion("user1", "get_achievements_count", 2)
    assert result == 2


def test_check_and_update_user_not_found():
    service = create_service()
    service.user_repo.get_profile.return_value = None
    result = service.check_and_update_quests("user1")
    assert result["success"] is False
    assert result["error"] == "Пользователь не найден"


def test_check_and_update_max_level():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 6}

    result = service.check_and_update_quests("user1")

    assert result["success"] is True
    assert result["max_level_reached"] is True
    assert result["leveled_up"] is False


def test_check_and_update_level_quests_not_found():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 1}
    service.get_level_quests = Mock(return_value=None)

    result = service.check_and_update_quests("user1")

    assert result["success"] is False
    assert result["error"] == "Задания для уровня 1 не найдены"


def test_check_and_update_complete_first_quest():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 1}

    service.get_level_quests = Mock(return_value={
        "quest1_type": "plant_first",
        "quest1_target": 1,
        "quest2_type": None,
        "quest2_target": None,
        "quest3_type": None,
        "quest3_target": None,
        "reward_type": "new_pot",
        "reward_value": "pot1",
        "reward_description": "Горшок"
    })

    service.get_user_level_progress = Mock(return_value={
        "quest1_completed": 0,
        "quest2_completed": 0,
        "quest3_completed": 0,
        "level_completed": 1
    })

    service._check_quest_completion = Mock(return_value=1)

    result = service.check_and_update_quests("user1")

    assert result["success"] is True
    assert result["leveled_up"] is False
    assert result["quests_completed"] == 1


def test_check_and_update_level_up():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 1}

    service.get_level_quests = Mock(return_value={
        "quest1_type": "plant_first",
        "quest1_target": 1,
        "quest2_type": None,
        "quest2_target": None,
        "quest3_type": None,
        "quest3_target": None,
        "reward_type": "new_pot",
        "reward_value": "pot1",
        "reward_description": "Горшок"
    })

    service.get_user_level_progress = Mock(return_value={
        "quest1_completed": 0,
        "quest2_completed": 0,
        "quest3_completed": 0,
        "level_completed": 0
    })

    service._check_quest_completion = Mock(return_value=1)
    service._claim_reward = Mock(return_value={"type": "new_pot"})

    result = service.check_and_update_quests("user1")

    assert result["success"] is True
    assert "leveled_up" in result


def test_trigger_quest_check():
    service = create_service()
    service.check_and_update_quests = Mock(return_value={"success": True})

    result = service.trigger_quest_check("user1", "water")

    assert result["success"] is True
    service.check_and_update_quests.assert_called_once_with("user1")


def test_get_all_quests_status():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 2}
    service.get_level_quests = Mock(return_value={})
    service.get_user_level_progress = Mock(return_value={"level_completed": True})

    result = service.get_all_quests_status("user1")

    assert len(result) == 6
    assert result[1]["status"] == "completed"


def test_claim_reward_returns_reward():
    service = create_service()

    quests = {
        "reward_type": "new_pot",
        "reward_value": "pot_1",
        "reward_description": "Новый горшок"
    }

    result = service._claim_reward("user1", 1, quests)

    assert result["type"] == "new_pot"
    assert result["value"] == "pot_1"
    assert result["description"] == "Новый горшок"


def test_claim_reward_achievement():
    service = create_service()
    service.challenge_repo.get_achievement_by_name.return_value = {"id": 55}

    quests = {
        "reward_type": "achievement",
        "reward_value": "Страж флоры",
        "reward_description": "Секретная ачивка"
    }

    result = service._claim_reward("user1", 5, quests)

    assert result["type"] == "achievement"
    service.challenge_repo.update_progress.assert_called_once_with("user1", 55, 1)
    service.challenge_repo.complete_achievement.assert_called_once_with("user1", 55)