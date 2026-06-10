"""
Тесты для UserService.

Проверяется:
- статистика пользователя;
- уровень пользователя;
- ежедневная серия входов;
- слоты растений;
- открытые дизайны;
- смена горшка и лейки.

Инструменты: pytest, unittest.mock.
"""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from datetime import date, timedelta
from unittest.mock import Mock

from backend.database_full.service.user_service import UserService


def create_service():
    service = UserService()
    service.user_repo = Mock()
    service.db = Mock()
    return service


def test_get_stats_profile_exists():
    service = create_service()

    service.user_repo.get_profile.return_value = {
        "current_level": 3,
        "max_plants_slots": 4,
        "current_plants_count": 2,
        "total_plants_grown": 10,
        "total_waterings": 25,
        "consecutive_days": 5,
        "best_streak": 8,
    }

    result = service.get_stats("user1")

    assert result["level"] == 3
    assert result["max_plants_slots"] == 4
    assert result["current_plants"] == 2
    assert result["total_plants_grown"] == 10
    assert result["total_waterings"] == 25
    assert result["consecutive_days"] == 5
    assert result["best_streak"] == 8


def test_get_stats_profile_not_found():
    service = create_service()
    service.user_repo.get_profile.return_value = None

    result = service.get_stats("user1")

    assert result["level"] == 1
    assert result["max_plants_slots"] == 1
    assert result["current_plants"] == 0
    assert result["total_plants_grown"] == 0
    assert result["total_waterings"] == 0
    assert result["consecutive_days"] == 0
    assert result["best_streak"] == 0


def test_get_current_level_success():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 4}

    assert service.get_current_level("user1") == 4


def test_get_current_level_default():
    service = create_service()
    service.user_repo.get_profile.return_value = None

    assert service.get_current_level("user1") == 1


def test_get_level_info_without_profile():
    service = create_service()
    service.user_repo.get_profile.return_value = None

    result = service.get_level_info("user1")

    assert result["current_level"] == 1
    assert result["max_level"] == 5
    assert result["next_level_quests"] is None


def test_get_level_info_max_level():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 5}

    result = service.get_level_info("user1")

    assert result["current_level"] == 5
    assert result["is_max_level"] is True


def test_get_level_info_with_next_quests():
    service = create_service()
    service.user_repo.get_profile.return_value = {"current_level": 2}
    service.db.execute_query.return_value = [
        {"quest1_type": "plant", "quest1_target": 1}
    ]

    result = service.get_level_info("user1")

    assert result["current_level"] == 2
    assert result["is_max_level"] is False
    assert result["next_level_quests"] == {"quest1_type": "plant", "quest1_target": 1}


def test_update_daily_streak_without_profile():
    service = create_service()
    service.user_repo.get_profile.return_value = None

    result = service.update_daily_streak("user1")

    assert result["success"] is False


def test_update_daily_streak_same_day():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "last_entry": date.today(),
        "consecutive_days": 4,
        "best_streak": 7,
    }

    result = service.update_daily_streak("user1")

    assert result["success"] is True
    assert result["consecutive_days"] == 4
    assert result["best_streak"] == 7
    assert result["streak_increased"] is False


def test_update_daily_streak_next_day():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "last_entry": date.today() - timedelta(days=1),
        "consecutive_days": 4,
        "best_streak": 7,
    }

    result = service.update_daily_streak("user1")

    assert result["success"] is True
    assert result["consecutive_days"] == 5
    assert result["best_streak"] == 7
    assert result["streak_increased"] is True
    service.user_repo.update_streak.assert_called_once()


def test_update_daily_streak_after_gap():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "last_entry": date.today() - timedelta(days=3),
        "consecutive_days": 4,
        "best_streak": 7,
    }

    result = service.update_daily_streak("user1")

    assert result["success"] is True
    assert result["consecutive_days"] == 1
    assert result["best_streak"] == 7
    assert result["streak_increased"] is True


def test_get_streak_info_profile_exists():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "consecutive_days": 3,
        "best_streak": 9,
    }

    result = service.get_streak_info("user1")

    assert result == {"consecutive_days": 3, "best_streak": 9}


def test_get_streak_info_profile_not_found():
    service = create_service()
    service.user_repo.get_profile.return_value = None

    result = service.get_streak_info("user1")

    assert result == {"consecutive_days": 0, "best_streak": 0}


def test_get_plant_slots_profile_exists():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "current_plants_count": 2,
        "max_plants_slots": 5,
    }

    result = service.get_plant_slots("user1")

    assert result["current"] == 2
    assert result["max"] == 5
    assert result["available"] == 3


def test_get_plant_slots_profile_not_found():
    service = create_service()
    service.user_repo.get_profile.return_value = None

    result = service.get_plant_slots("user1")

    assert result == {"current": 0, "max": 1, "available": 1}


def test_has_free_slot_true():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "current_plants_count": 1,
        "max_plants_slots": 3,
    }

    assert service.has_free_slot("user1") is True


def test_has_free_slot_false():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "current_plants_count": 3,
        "max_plants_slots": 3,
    }

    assert service.has_free_slot("user1") is False


def test_get_unlocked_pots_default():
    service = create_service()
    service.user_repo.get_profile.return_value = None

    assert service.get_unlocked_pots("user1") == ["standard"]


def test_get_unlocked_pots_from_profile():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "unlocked_pots": '["standard", "2"]'
    }

    assert service.get_unlocked_pots("user1") == ["standard", "2"]


def test_get_current_designs_default():
    service = create_service()
    service.user_repo.get_profile.return_value = None

    assert service.get_current_designs("user1") == {
        "pot": "standard",
        "watering_can": "standard",
    }


def test_get_current_designs_from_profile():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "current_pot": "2",
        "current_watering_can": "1",
    }

    result = service.get_current_designs("user1")

    assert result["pot"] == "2"
    assert result["watering_can"] == "1"


def test_change_pot_not_unlocked():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "unlocked_pots": '["standard"]'
    }

    result = service.change_pot("user1", "2")

    assert result["success"] is False
    assert result["error"] == "Горшок не открыт"


def test_change_pot_success():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "unlocked_pots": '["standard", "2"]'
    }
    service.db.execute_update.return_value = True

    result = service.change_pot("user1", "2")

    assert result["success"] is True


def test_change_watering_can_not_unlocked():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "current_level": 1,
        "unlocked_watering_cans": '["standard"]',
    }

    result = service.change_watering_can("user1", "2")

    assert result["success"] is False
    assert result["error"] == "Лейка не открыта"


def test_change_watering_can_success_by_level():
    service = create_service()
    service.user_repo.get_profile.return_value = {
        "current_level": 4,
        "unlocked_watering_cans": '["standard"]',
    }
    service.db.execute_update.return_value = True
    service.user_repo.unlock_watering_can.return_value = True

    result = service.change_watering_can("user1", "2")

    assert result["success"] is True
    service.user_repo.unlock_watering_can.assert_called_once_with("user1", "2")


def test_increment_current_plants():
    service = create_service()
    service.user_repo.update_current_plants_count.return_value = True

    assert service.increment_current_plants("user1", 1) is True


def test_increment_stat():
    service = create_service()
    service.user_repo.increment_stat.return_value = True

    assert service.increment_stat("user1", "total_waterings") is True


def test_add_plant_slot():
    service = create_service()
    service.user_repo.update_plant_slots.return_value = True

    assert service.add_plant_slot("user1") is True