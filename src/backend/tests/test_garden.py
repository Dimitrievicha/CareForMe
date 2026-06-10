import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = SRC_DIR / "backend"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from backend.app import app
import web.garden as garden_module


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login_as_test_user(client):
    with client.session_transaction() as session:
        session["user_id"] = "test_user_id"


def test_get_garden_without_auth(client):
    response = client.get("/api/garden/")
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_garden_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.flower_interface,
        "get_my_garden",
        lambda user_id, only_alive=True: [
            {
                "id": "1",
                "custom_name": "Мой цветок",
                "last_watered": None
            }
        ]
    )

    response = client.get("/api/garden/")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert len(data["garden"]) == 1
    assert data["garden"][0]["days_since_watered"] == 0


def test_get_stats_without_auth(client):
    response = client.get("/api/garden/stats")
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_stats_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.user_interface,
        "get_stats",
        lambda user_id: {
            "level": 3,
            "total_waterings": 10,
            "total_plants_grown": 5,
            "total_mistakes": 2
        }
    )

    monkeypatch.setattr(
        garden_module.user_interface,
        "get_plant_slots_info",
        lambda user_id: {
            "current": 2,
            "max": 4
        }
    )

    monkeypatch.setattr(
        garden_module.user_interface,
        "get_streak_info",
        lambda user_id: {
            "consecutive_days": 7,
            "best_streak": 12
        }
    )

    response = client.get("/api/garden/stats")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["level"] == 3
    assert data["streak"] == 7
    assert data["best_streak"] == 12
    assert data["current_plants"] == 2
    assert data["max_slots"] == 4


def test_available_plants_success(client):
    response = client.get("/api/garden/available_plants")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert len(data["plants"]) == 3

    names = [p["name"] for p in data["plants"]]

    assert "Спатифиллум" in names
    assert "Кактус" in names
    assert "Фикус" in names


def test_change_pot_without_auth(client):
    response = client.post(
        "/api/garden/change_pot",
        json={"pot_id": "1"}
    )
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False


def test_change_pot_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.user_interface,
        "change_pot",
        lambda user_id, pot_id: {
            "success": True
        }
    )

    response = client.post(
        "/api/garden/change_pot",
        json={"pot_id": "2"}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True


def test_change_can_without_auth(client):
    response = client.post(
        "/api/garden/change_can",
        json={"can_id": "1"}
    )
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False


def test_change_can_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.user_interface,
        "change_watering_can",
        lambda user_id, can_id: {
            "success": True
        }
    )

    response = client.post(
        "/api/garden/change_can",
        json={"can_id": "2"}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True


def test_plant_without_auth(client):
    response = client.post("/api/garden/plant", json={"species_id": 1})

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False


def test_plant_no_free_slots(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.user_interface,
        "has_free_slot",
        lambda user_id: False
    )

    response = client.post("/api/garden/plant", json={"species_id": 1})
    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Нет свободных слотов"


def test_plant_backend_error(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.user_interface,
        "has_free_slot",
        lambda user_id: True
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "plant_flower",
        lambda user_id, species_id, custom_name: {
            "success": False,
            "error": "Ошибка посадки"
        }
    )

    response = client.post("/api/garden/plant", json={"species_id": 1})
    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Ошибка посадки"


def test_plant_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.user_interface,
        "has_free_slot",
        lambda user_id: True
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "plant_flower",
        lambda user_id, species_id, custom_name: {
            "success": True,
            "plant_id": "p1",
            "plant_name": "Мой цветок",
            "species_name": "Кактус"
        }
    )

    monkeypatch.setattr(
        garden_module.level_quest_interface,
        "trigger_check",
        lambda user_id, action: {}
    )

    response = client.post(
        "/api/garden/plant",
        json={"species_id": 2, "custom_name": "Мой цветок"}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["plant"]["plant_id"] == "p1"
    assert data["plant"]["plant_name"] == "Мой цветок"
    assert data["plant"]["species_name"] == "Кактус"


def test_plant_success_with_quest_and_level_up(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.user_interface,
        "has_free_slot",
        lambda user_id: True
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "plant_flower",
        lambda user_id, species_id, custom_name: {
            "success": True,
            "plant_id": "p2",
            "plant_name": "Фикус",
            "species_name": "Фикус"
        }
    )

    monkeypatch.setattr(
        garden_module.level_quest_interface,
        "trigger_check",
        lambda user_id, action: {
            "quests_completed": 1,
            "leveled_up": True,
            "new_level": 2,
            "reward": {"type": "slot"}
        }
    )

    response = client.post(
        "/api/garden/plant",
        json={"species_id": 3, "custom_name": "Фикус"}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["quest_update"]["quest_completed"] == 1
    assert data["level_up"]["new_level"] == 2


def test_water_without_auth(client):
    response = client.post("/api/garden/water/test")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False


def test_water_error(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.flower_interface,
        "water_flower",
        lambda plant_id, user_id: {
            "success": False,
            "error": "Нельзя полить"
        }
    )

    response = client.post("/api/garden/water/test")
    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Нельзя полить"


def test_water_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.flower_interface,
        "water_flower",
        lambda plant_id, user_id: {
            "success": True,
            "message": "Полито"
        }
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: {
            "health_status": "healthy",
            "growth_stage": "seedling",
            "growth_progress": 50
        }
    )

    monkeypatch.setattr(
        garden_module.level_quest_interface,
        "trigger_check",
        lambda user_id, action: {}
    )

    monkeypatch.setattr(
        garden_module.challenge_interface,
        "check_all_achievements",
        lambda user_id: []
    )

    response = client.post("/api/garden/water/test")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["message"] == "Полито"
    assert data["plant_status"]["health"] == "healthy"


def test_water_success_with_warning_achievement_and_level_up(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.flower_interface,
        "water_flower",
        lambda plant_id, user_id: {
            "success": True,
            "message": "Полито",
            "warning": "Возможен перелив"
        }
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: {
            "health_status": "healthy",
            "growth_stage": "growing",
            "growth_progress": 80
        }
    )

    monkeypatch.setattr(
        garden_module.level_quest_interface,
        "trigger_check",
        lambda user_id, action: {
            "quests_completed": 2,
            "leveled_up": True,
            "new_level": 3,
            "reward": {"type": "new_plant"}
        }
    )

    monkeypatch.setattr(
        garden_module.challenge_interface,
        "check_all_achievements",
        lambda user_id: [
            {
                "name": "Заботливый родитель",
                "description": "Первое растение полито"
            }
        ]
    )

    response = client.post("/api/garden/water/test")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["warning"] == "Возможен перелив"
    assert data["achievement"]["name"] == "Заботливый родитель"
    assert data["quest_update"]["quest_completed"] == 2
    assert data["level_up"]["new_level"] == 3


def test_check_all_without_auth(client):
    response = client.post("/api/garden/check_all")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False


def test_check_all_success_without_updates(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.flower_interface,
        "get_my_garden",
        lambda user_id, only_alive=True: [
            {
                "id": "1",
                "custom_name": "Кактус",
                "growth_stage": "seed"
            }
        ]
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "check_health",
        lambda plant_id, user_id: {
            "health_status": "healthy",
            "warning": None
        }
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "update_growth",
        lambda plant_id, user_id: {
            "stage_changed": False,
            "new_progress": 10
        }
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "check_death",
        lambda plant_id, user_id: {
            "is_dead": False
        }
    )

    monkeypatch.setattr(
        garden_module.challenge_interface,
        "check_all_achievements",
        lambda user_id: []
    )

    monkeypatch.setattr(
        garden_module.level_quest_interface,
        "trigger_check",
        lambda user_id, action: {}
    )

    response = client.post("/api/garden/check_all")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["updates"] == []
    assert data["quest_update"] is None


def test_check_all_success_with_updates(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        garden_module.flower_interface,
        "get_my_garden",
        lambda user_id, only_alive=True: [
            {
                "id": "1",
                "custom_name": "Кактус",
                "growth_stage": "seed"
            }
        ]
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "check_health",
        lambda plant_id, user_id: {
            "health_status": "wilting",
            "warning": "Полить скоро"
        }
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "update_growth",
        lambda plant_id, user_id: {
            "stage_changed": True,
            "new_stage": "seedling",
            "new_progress": 20
        }
    )

    monkeypatch.setattr(
        garden_module.flower_interface,
        "check_death",
        lambda plant_id, user_id: {
            "is_dead": False
        }
    )

    monkeypatch.setattr(
        garden_module.challenge_interface,
        "check_all_achievements",
        lambda user_id: [
            {
                "name": "Страж флоры"
            }
        ]
    )

    monkeypatch.setattr(
        garden_module.level_quest_interface,
        "trigger_check",
        lambda user_id, action: {
            "quests_completed": 3,
            "leveled_up": True
        }
    )

    response = client.post("/api/garden/check_all")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert len(data["updates"]) == 1
    assert data["updates"][0]["plant_id"] == "1"
    assert data["updates"][0]["growth_stage"] == "seedling"
    assert data["new_achievements"] == [{"name": "Страж флоры"}]
    assert data["quest_update"]["quest_completed"] == 3