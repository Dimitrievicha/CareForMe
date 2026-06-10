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