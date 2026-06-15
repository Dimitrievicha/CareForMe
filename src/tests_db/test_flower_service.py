"""
Тесты для FlowerService.

Проверяется:
- посадка растения;
- полив растения;
- ошибки доступа к чужим/несуществующим растениям.

Инструменты: pytest, unittest.mock.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import Mock, patch

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from backend.database_full.service.flower_service import FlowerService


def create_service():
    service = FlowerService()
    service.plant_repo = Mock()
    service.user_repo = Mock()
    service.mistake_repo = Mock()
    service.challenge_repo = Mock()
    service.db = Mock()
    return service


def test_plant_flower_template_not_found():
    service = create_service()

    service.plant_repo.get_template_by_species_id.return_value = None

    result = service.plant_flower("user1", 999, "Unknown")

    assert result["success"] is False
    assert result["error"] == "Растение не найдено"


def test_plant_flower_user_not_found():
    service = create_service()

    service.plant_repo.get_template_by_species_id.return_value = {
        "id": 1,
        "species_name": "Кактус"
    }
    service.user_repo.get_profile.return_value = None

    result = service.plant_flower("user1", 1, "My plant")

    assert result["success"] is False
    assert result["error"] == "Пользователь не найден"


def test_plant_flower_no_free_slots():
    service = create_service()

    service.plant_repo.get_template_by_species_id.return_value = {
        "id": 1,
        "species_name": "Кактус"
    }
    service.user_repo.get_profile.return_value = {
        "current_plants_count": 3,
        "max_plants_slots": 3
    }

    result = service.plant_flower("user1", 1, "My plant")

    assert result["success"] is False
    assert result["error"] == "Нет свободных слотов"


@patch("backend.database_full.service.flower_service.level_quest_service")
def test_plant_flower_create_error(mock_level_quest_service):
    service = create_service()

    service.plant_repo.get_template_by_species_id.return_value = {
        "id": 1,
        "species_name": "Кактус"
    }
    service.user_repo.get_profile.return_value = {
        "current_plants_count": 0,
        "max_plants_slots": 3
    }
    service.plant_repo.create_user_plant.return_value = False

    result = service.plant_flower("user1", 1, "My plant")

    assert result["success"] is False
    assert result["error"] == "Ошибка посадки"


@patch("backend.database_full.service.flower_service.level_quest_service")
def test_plant_flower_success(mock_level_quest_service):
    service = create_service()

    service.plant_repo.get_template_by_species_id.return_value = {
        "id": 1,
        "species_name": "Кактус"
    }
    service.user_repo.get_profile.return_value = {
        "current_plants_count": 0,
        "max_plants_slots": 3
    }
    service.plant_repo.create_user_plant.return_value = True

    result = service.plant_flower("user1", 1, "My cactus")

    assert result["success"] is True
    assert result["plant_name"] == "My cactus"
    assert result["species_name"] == "Кактус"
    assert result["species_id"] == 1

    service.user_repo.update_current_plants_count.assert_called_once_with("user1", 1)
    service.user_repo.increment_stat.assert_called_once_with("user1", "total_plants_grown")
    mock_level_quest_service.trigger_quest_check.assert_called_once_with("user1", "plant")


def test_water_flower_plant_not_found():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = None

    result = service.water_flower("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение не найдено"


def test_water_flower_another_user():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "other_user"
    }

    result = service.water_flower("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Это не ваше растение"


def test_water_flower_dead_plant():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": False
    }

    result = service.water_flower("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение мертво. Посадите новое!"


def test_water_flower_already_watered_today():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "last_watered": date.today().isoformat()
    }

    result = service.water_flower("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Уже полито сегодня"


@patch("backend.database_full.service.flower_service.level_quest_service")
def test_water_flower_success(mock_level_quest_service):
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "last_watered": (date.today() - timedelta(days=5)).isoformat(),
        "water_interval_min": 3,
        "custom_name": "Кактус"
    }

    result = service.water_flower("plant1", "user1")

    assert result["success"] is True
    assert result["plant_name"] == "Кактус"
    assert result["was_overwatered"] is False

    service.plant_repo.water_plant.assert_called_once_with("plant1")
    service.user_repo.increment_stat.assert_called_once_with("user1", "total_waterings")
    mock_level_quest_service.trigger_quest_check.assert_called_once_with("user1", "water")


@patch("backend.database_full.service.flower_service.level_quest_service")
def test_water_flower_overwatered(mock_level_quest_service):
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "last_watered": (date.today() - timedelta(days=1)).isoformat(),
        "water_interval_min": 3,
        "custom_name": "Кактус"
    }

    result = service.water_flower("plant1", "user1")

    assert result["success"] is True
    assert result["was_overwatered"] is True
    assert result["warning"] == "Осторожно! Возможно, вы поливаете слишком часто."

    service.mistake_repo.add_mistake.assert_called_once_with(
        "user1",
        "plant1",
        "overwater"
    )
# =========================
# set_light_level()
# =========================

def test_set_light_level_plant_not_found():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = None

    assert service.set_light_level("plant1", "user1", "high") is False


def test_set_light_level_not_owner():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "other_user"
    }

    assert service.set_light_level("plant1", "user1", "high") is False


def test_set_light_level_success():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1"
    }

    service.plant_repo.update_light_level.return_value = True

    assert service.set_light_level("plant1", "user1", "high") is True


# =========================
# set_location()
# =========================

def test_set_location_plant_not_found():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = None

    assert service.set_location("plant1", "user1", "Балкон") is False


def test_set_location_not_owner():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "other_user"
    }

    assert service.set_location("plant1", "user1", "Балкон") is False


def test_set_location_success():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1"
    }

    service.plant_repo.update_location.return_value = True

    assert service.set_location("plant1", "user1", "Балкон") is True


# =========================
# get_all_growth_stages()
# =========================

def test_get_all_growth_stages():
    service = create_service()

    service.plant_repo.get_user_plants.return_value = [
        {"growth_stage": "seed"},
        {"growth_stage": "seedling"},
        {"growth_stage": "seedling"},
        {"growth_stage": "mature"},
    ]

    result = service.get_all_growth_stages("user1")

    assert result["seed"] == 1
    assert result["seedling"] == 2
    assert result["growing"] == 0
    assert result["mature"] == 1
    assert result["flowering"] == 0
# =========================
# check_health()
# =========================

def test_check_health_plant_not_found():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = None

    result = service.check_health("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение не найдено"


def test_check_health_not_owner():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "other_user"
    }

    result = service.check_health("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение не найдено"


def test_check_health_dead_plant():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": False,
        "custom_name": "Кактус",
        "death_cause": "drought"
    }

    result = service.check_health("plant1", "user1")

    assert result["success"] is True
    assert result["is_alive"] is False
    assert result["health_status"] == "dead"
    assert result["death_cause"] == "drought"


def test_check_health_healthy_plant():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "custom_name": "Кактус",
        "last_watered": date.today().isoformat(),
        "water_interval_min": 3,
        "water_interval_max": 7,
        "health_status": "healthy"
    }

    result = service.check_health("plant1", "user1")

    assert result["success"] is True
    assert result["health_status"] == "healthy"
    assert result["warning"] is None


def test_check_health_wilting_plant():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "custom_name": "Кактус",
        "last_watered": (date.today() - timedelta(days=8)).isoformat(),
        "water_interval_min": 3,
        "water_interval_max": 7,
        "health_status": "healthy"
    }

    result = service.check_health("plant1", "user1")

    assert result["success"] is True
    assert result["health_status"] == "wilting"
    assert result["warning"] == "Кактус увядает. Пора поливать!"
    service.plant_repo.update_health_status.assert_called_once_with("plant1", "wilting")


def test_check_health_dying_plant():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "custom_name": "Кактус",
        "last_watered": (date.today() - timedelta(days=15)).isoformat(),
        "water_interval_min": 3,
        "water_interval_max": 7,
        "health_status": "wilting"
    }

    result = service.check_health("plant1", "user1")

    assert result["success"] is True
    assert result["health_status"] == "dying"
    assert result["warning"] == "Кактус умирает! Срочно полейте!"
    service.plant_repo.update_health_status.assert_called_once_with("plant1", "dying")
# =========================
# update_growth()
# =========================

def test_update_growth_plant_not_found():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = None

    result = service.update_growth("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение не найдено"


def test_update_growth_not_owner():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "other_user"
    }

    result = service.update_growth("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение не найдено"


def test_update_growth_dead_plant():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": False
    }

    result = service.update_growth("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение мертво"


def test_update_growth_healthy_plant():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "custom_name": "Кактус",
        "growth_stage": "seed",
        "growth_progress": 0,
        "health_status": "healthy"
    }

    result = service.update_growth("plant1", "user1")

    assert result["success"] is True
    assert result["old_progress"] == 0
    assert result["new_progress"] == 10
    assert result["stage_changed"] is False
    service.plant_repo.update_growth.assert_called_once_with("plant1", "seed", 10)


def test_update_growth_wilting_plant():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "custom_name": "Кактус",
        "growth_stage": "seed",
        "growth_progress": 20,
        "health_status": "wilting"
    }

    result = service.update_growth("plant1", "user1")

    assert result["success"] is True
    assert result["new_progress"] == 25
    assert result["new_stage"] == "seedling"
    assert result["stage_changed"] is True


@patch("backend.database_full.service.flower_service.level_quest_service")
def test_update_growth_to_mature_without_mistakes(mock_level_quest_service):
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True,
        "custom_name": "Фикус",
        "growth_stage": "growing",
        "growth_progress": 70,
        "health_status": "healthy"
    }

    service.mistake_repo.get_mistakes_count.return_value = 0

    result = service.update_growth("plant1", "user1")

    assert result["success"] is True
    assert result["new_stage"] == "mature"
    assert result["stage_changed"] is True
    mock_level_quest_service.trigger_quest_check.assert_called_once_with(
        "user1",
        "grow_to_mature"
    )
    service.plant_repo.mark_perfect_growth.assert_called_once_with("plant1")


# =========================
# revive_plant()
# =========================

def test_revive_plant_not_found():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = None

    result = service.revive_plant("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение не найдено"


def test_revive_plant_not_owner():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "other_user"
    }

    result = service.revive_plant("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение не найдено"


def test_revive_plant_alive():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": True
    }

    result = service.revive_plant("plant1", "user1")

    assert result["success"] is False
    assert result["error"] == "Растение еще живо!"


def test_revive_plant_success():
    service = create_service()

    service.plant_repo.get_user_plant_by_id.return_value = {
        "user_id": "user1",
        "is_alive": False,
        "custom_name": "Кактус"
    }

    result = service.revive_plant("plant1", "user1")

    assert result["success"] is True
    assert result["plant_name"] == "Кактус"
    service.plant_repo.revive_plant.assert_called_once_with("plant1")
    service.user_repo.update_current_plants_count.assert_called_once_with("user1", 1)