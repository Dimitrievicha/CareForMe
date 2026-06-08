import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = SRC_DIR / "backend"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from backend.app import app
import web.plants as plants_module


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login_as_test_user(client):
    with client.session_transaction() as session:
        session["user_id"] = "test_user_id"


def test_get_plant_without_auth(client):
    response = client.get("/api/plants/plant_1")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_set_light_without_auth(client):
    response = client.post(
        "/api/plants/plant_1/light",
        json={"light_level": "medium"}
    )

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_set_location_without_auth(client):
    response = client.post(
        "/api/plants/plant_1/location",
        json={"location": "room"}
    )

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_revive_without_auth(client):
    response = client.post(
        "/api/plants/plant_1/revive",
        json={"custom_name": "New plant"}
    )

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_plant_not_found(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        plants_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: None
    )

    response = client.get("/api/plants/unknown_plant")

    data = response.get_json()

    assert response.status_code == 404
    assert data["success"] is False
    assert data["error"] == "Растение не найдено"


def test_get_plant_success(client, monkeypatch):
    login_as_test_user(client)

    fake_plant = {
        "id": "plant_1",
        "custom_name": "Ромашка",
        "species_id": 1,
        "species_name": "Ромашка",
        "last_watered": None,
        "is_alive": True
    }

    monkeypatch.setattr(
        plants_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: fake_plant
    )

    response = client.get("/api/plants/plant_1")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["plant"]["id"] == "plant_1"
    assert data["plant"]["days_since_watered"] == 0


def test_set_light_invalid_value(client):
    login_as_test_user(client)

    response = client.post(
        "/api/plants/plant_1/light",
        json={"light_level": "very_bright"}
    )

    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Допустимые значения: low, medium, high"


def test_set_light_plant_not_found(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        plants_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: None
    )

    response = client.post(
        "/api/plants/plant_1/light",
        json={"light_level": "medium"}
    )

    data = response.get_json()

    assert response.status_code == 404
    assert data["success"] is False
    assert data["error"] == "Растение не найдено"


def test_set_light_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        plants_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: {"id": plant_id}
    )
    monkeypatch.setattr(
        plants_module.flower_interface,
        "set_light_level",
        lambda plant_id, user_id, light_level: True
    )
    monkeypatch.setattr(
        plants_module.flower_interface,
        "check_health",
        lambda plant_id, user_id: {
            "health_status": "healthy",
            "warning": None
        }
    )

    response = client.post(
        "/api/plants/plant_1/light",
        json={"light_level": "medium"}
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["health_status"] == "healthy"


def test_set_location_empty_value(client):
    login_as_test_user(client)

    response = client.post(
        "/api/plants/plant_1/location",
        json={"location": ""}
    )

    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Укажите location"


def test_set_location_plant_not_found(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        plants_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: None
    )

    response = client.post(
        "/api/plants/plant_1/location",
        json={"location": "balcony"}
    )

    data = response.get_json()

    assert response.status_code == 404
    assert data["success"] is False
    assert data["error"] == "Растение не найдено"


def test_set_location_success_for_ficus(client, monkeypatch):
    login_as_test_user(client)

    fake_plant = {
        "id": "plant_1",
        "species_id": 3,
        "location": "room"
    }

    monkeypatch.setattr(
        plants_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: fake_plant
    )
    monkeypatch.setattr(
        plants_module.flower_interface,
        "set_location",
        lambda plant_id, user_id, location: True
    )

    response = client.post(
        "/api/plants/plant_1/location",
        json={"location": "balcony"}
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["stress_warning"] is not None


def test_revive_alive_plant(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        plants_module.flower_interface,
        "get_plant_details",
        lambda plant_id, user_id: {
            "id": plant_id,
            "species_id": 1,
            "is_alive": True
        }
    )

    response = client.post(
        "/api/plants/plant_1/revive",
        json={"custom_name": "New plant"}
    )

    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Растение живо — возрождение не нужно"


def test_catalog_success(client, monkeypatch):
    class FakePlantRepository:
        def get_all_templates(self):
            return [
                {
                    "species_id": 1,
                    "species_name": "Ромашка",
                    "nickname": "Солнечная",
                    "description": "Описание",
                    "character_trait": "Добрая",
                    "water_interval_min": 2,
                    "water_interval_max": 4,
                    "light_requirement": "medium",
                    "watering_advice": "Поливать умеренно",
                    "light_advice": "Средний свет",
                    "why_disease": "",
                    "tips": "Совет 1|Совет 2",
                    "symptoms": "Желтые листья|Сухость",
                    "flowering_conditions": "Хороший уход",
                    "unlock_level": 1
                }
            ]

    monkeypatch.setattr(plants_module, "PlantRepository", FakePlantRepository)

    response = client.get("/api/plants/catalog")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert len(data["plants"]) == 1
    assert data["plants"][0]["species_name"] == "Ромашка"