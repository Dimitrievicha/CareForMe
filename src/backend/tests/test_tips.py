"""
Автоматизированные тесты Backend API.

Проверяются позитивные и негативные сценарии работы эндпоинтов.

Инструменты: pytest, Flask Test Client.
"""
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = SRC_DIR / "backend"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from backend.app import app
import web.tips as tips_module


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login_as_test_user(client):
    with client.session_transaction() as session:
        session["user_id"] = "test_user_id"


def test_get_all_tips_without_auth(client):
    response = client.get("/api/tips/")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_all_tips_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        tips_module.tips_interface,
        "get_all_tips",
        lambda: ["Совет 1", "Совет 2"]
    )

    response = client.get("/api/tips/")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["tips"] == ["Совет 1", "Совет 2"]


def test_get_positive_tips_without_auth(client):
    response = client.get("/api/tips/positive")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_positive_tips_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        tips_module.tips_interface,
        "get_positive_tips",
        lambda: ["Ты справишься"]
    )

    response = client.get("/api/tips/positive")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["tips"] == ["Ты справишься"]


def test_get_tip_by_type_without_auth(client):
    response = client.get("/api/tips/by_type/watering")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_tip_by_type_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        tips_module.tips_interface,
        "get_tip_by_type",
        lambda tip_type: {"type": tip_type, "text": "Поливай умеренно"}
    )

    response = client.get("/api/tips/by_type/watering")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["tip"]["type"] == "watering"
    assert data["tip"]["text"] == "Поливай умеренно"


def test_get_plant_tips_without_auth(client):
    response = client.get("/api/tips/for_plant/1")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_plant_tips_not_found(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        tips_module.tips_interface,
        "get_plant_tips",
        lambda species_id: None
    )

    response = client.get("/api/tips/for_plant/999")

    data = response.get_json()

    assert response.status_code == 404
    assert data["success"] is False
    assert data["error"] == "Вид 999 не найден"


def test_get_plant_tips_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        tips_module.tips_interface,
        "get_plant_tips",
        lambda species_id: {
            "species_id": species_id,
            "tips": ["Не переливать", "Держать на свету"]
        }
    )

    response = client.get("/api/tips/for_plant/1")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["species_id"] == 1
    assert data["tips"] == ["Не переливать", "Держать на свету"]