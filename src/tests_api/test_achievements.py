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
import web.achievements as achievements_module


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login_as_test_user(client):
    with client.session_transaction() as session:
        session["user_id"] = "test_user_id"


def test_get_achievements_without_auth(client):
    response = client.get("/api/achievements/")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_achievements_success(client, monkeypatch):
    login_as_test_user(client)

    fake_achievements = [
        {"name": "Заботливый родитель", "is_completed": True},
        {"name": "Коллекционер", "is_completed": False},
        {"name": "Страж флоры", "is_completed": True},
    ]

    fake_stats = {
        "plants_grown_to_maturity_perfect": 2,
        "species_collected": 3,
        "mistake_count": 1,
        "death_count": 0,
        "level": 4,
    }

    monkeypatch.setattr(
        achievements_module.challenge_interface,
        "get_all_achievements",
        lambda user_id: fake_achievements
    )

    monkeypatch.setattr(
        achievements_module.challenge_interface,
        "get_statistics",
        lambda user_id: fake_stats
    )

    response = client.get("/api/achievements/")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert len(data["achievements"]) == 3
    assert data["stats"]["total_achievements"] == 2
    assert data["stats"]["plants_perfect"] == 2
    assert data["stats"]["species_collected"] == 3
    assert data["stats"]["mistakes_count"] == 1
    assert data["stats"]["deaths_count"] == 0
    assert data["stats"]["level"] == 4


def test_check_achievements_without_auth(client):
    response = client.post("/api/achievements/check")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_check_achievements_success_with_known_icon(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        achievements_module.challenge_interface,
        "check_all_achievements",
        lambda user_id: [
            {
                "name": "Заботливый родитель",
                "description": "Первое растение посажено"
            }
        ]
    )

    response = client.post("/api/achievements/check")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["new_achievements"][0]["name"] == "Заботливый родитель"
    assert data["new_achievements"][0]["icon"] == "🌱"


def test_check_achievements_success_with_default_icon(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        achievements_module.challenge_interface,
        "check_all_achievements",
        lambda user_id: [
            {
                "name": "Неизвестное достижение",
                "description": "Описание"
            }
        ]
    )

    response = client.post("/api/achievements/check")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["new_achievements"][0]["icon"] == "🏆"


def test_get_recent_achievements_without_auth(client):
    response = client.get("/api/achievements/recent")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_recent_achievements_success(client, monkeypatch):
    login_as_test_user(client)

    completed = [
        {"name": "A"},
        {"name": "B"},
        {"name": "C"},
        {"name": "D"},
    ]

    monkeypatch.setattr(
        achievements_module.challenge_interface,
        "get_completed",
        lambda user_id: completed
    )

    response = client.get("/api/achievements/recent")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["recent"] == [{"name": "B"}, {"name": "C"}, {"name": "D"}]