"""
Автоматизированные тесты Backend API.

Проверяются позитивные и негативные сценарии работы эндпоинтов.

Инструменты: pytest, Flask Test Client.
"""
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = SRC_DIR / "backend"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from backend.app import app
import web.game_state as game_module


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login_as_test_user(client):
    with client.session_transaction() as session:
        session["user_id"] = "test_user_id"


def test_save_game_state_without_auth(client):
    response = client.post(
        "/api/game/save",
        json={
            "slotData": {},
            "currentLevel": 1,
            "achievements": {}
        }
    )

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Необходима авторизация"


def test_save_game_state_without_data(client):
    login_as_test_user(client)

    response = client.post("/api/game/save", json={})

    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Нет данных"


def test_save_game_state_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        game_module.game_interface,
        "save_state",
        lambda user_id, slot_data, current_level, achievements: True
    )

    response = client.post(
        "/api/game/save",
        json={
            "slotData": {"slot1": "plant_1"},
            "currentLevel": 2,
            "achievements": {"firstPlant": True}
        }
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True


def test_save_game_state_error(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        game_module.game_interface,
        "save_state",
        lambda user_id, slot_data, current_level, achievements: False
    )

    response = client.post(
        "/api/game/save",
        json={
            "slotData": {"slot1": "plant_1"},
            "currentLevel": 2,
            "achievements": {}
        }
    )

    data = response.get_json()

    assert response.status_code == 500
    assert data["success"] is False
    assert data["error"] == "Ошибка сохранения"


def test_load_game_state_without_auth(client):
    response = client.get("/api/game/load")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Необходима авторизация"


def test_load_game_state_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        game_module.game_interface,
        "load_state",
        lambda user_id: {
            "slotData": {"slot1": "plant_1"},
            "currentLevel": 3,
            "achievements": {"firstPlant": True}
        }
    )

    response = client.get("/api/game/load")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["slotData"] == {"slot1": "plant_1"}
    assert data["currentLevel"] == 3
    assert data["achievements"] == {"firstPlant": True}