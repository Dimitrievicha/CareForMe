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
import web.quests as quests_module


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login_as_test_user(client):
    with client.session_transaction() as session:
        session["user_id"] = "test_user_id"


def test_get_all_quests_success(client, monkeypatch):
    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_all_levels_quests",
        lambda: [{"level": 1, "quests": []}]
    )

    response = client.get("/api/quests/")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["levels"] == [{"level": 1, "quests": []}]


def test_get_progress_without_auth(client):
    response = client.get("/api/quests/progress")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_progress_success_with_reward(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        quests_module.user_interface,
        "get_current_level",
        lambda user_id: 2
    )

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_current_level_progress",
        lambda user_id: {
            "quests": [{"number": 1, "completed": True}],
            "all_completed": False
        }
    )

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_reward_info",
        lambda level: {
            "reward_type": "slot",
            "reward_description": "Новый слот"
        }
    )

    response = client.get("/api/quests/progress")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["level"] == 2
    assert data["quests"] == [{"number": 1, "completed": True}]
    assert data["all_completed"] is False
    assert data["next_reward"] == {
        "type": "slot",
        "description": "Новый слот"
    }


def test_get_progress_success_level_five_without_next_reward(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        quests_module.user_interface,
        "get_current_level",
        lambda user_id: 5
    )

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_current_level_progress",
        lambda user_id: {
            "quests": [],
            "all_completed": True
        }
    )

    response = client.get("/api/quests/progress")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["level"] == 5
    assert data["next_reward"] is None


def test_get_level_quests_without_auth(client):
    response = client.get("/api/quests/level/1")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_level_quests_invalid_level(client):
    login_as_test_user(client)

    response = client.get("/api/quests/level/6")

    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Уровень должен быть от 1 до 5"


def test_get_level_quests_not_found(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_level_quests",
        lambda level: None
    )

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_user_progress",
        lambda user_id, level: None
    )

    response = client.get("/api/quests/level/3")

    data = response.get_json()

    assert response.status_code == 404
    assert data["success"] is False
    assert data["error"] == "Задания для уровня 3 не найдены"


def test_get_level_quests_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_level_quests",
        lambda level: {
            "quest1_type": "water",
            "quest1_description": "Полить растение",
            "quest1_target": 1,
            "quest2_type": "plant",
            "quest2_description": "Посадить растение",
            "quest2_target": 1,
            "quest3_type": None,
            "reward_type": "slot",
            "reward_value": "1",
            "reward_description": "Новый слот"
        }
    )

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_user_progress",
        lambda user_id, level: {"level_completed": True}
    )

    response = client.get("/api/quests/level/2")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["level"] == 2
    assert len(data["quests"]) == 2
    assert data["reward"]["type"] == "slot"
    assert data["is_completed"] is True


def test_check_quests_without_auth(client):
    response = client.post("/api/quests/check")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_check_quests_success_without_level_up(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "check_quests",
        lambda user_id: {
            "leveled_up": False,
            "quests_completed": 2
        }
    )

    response = client.post("/api/quests/check")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["leveled_up"] is False
    assert data["completed_quests"] == [2]


def test_check_quests_success_with_level_up(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "check_quests",
        lambda user_id: {
            "leveled_up": True,
            "new_level": 3,
            "reward": {"type": "slot"},
            "quests_completed": 1
        }
    )

    response = client.post("/api/quests/check")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["leveled_up"] is True
    assert data["new_level"] == 3
    assert data["reward"] == {"type": "slot"}
    assert data["completed_quests"] == [1]


def test_get_reward_success(client, monkeypatch):
    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_reward_info",
        lambda level: {
            "reward_type": "slot",
            "reward_value": "1",
            "reward_description": "Новый слот"
        }
    )

    response = client.get("/api/quests/reward/2")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["reward"]["reward_type"] == "slot"


def test_get_reward_not_found(client, monkeypatch):
    monkeypatch.setattr(
        quests_module.level_quest_interface,
        "get_reward_info",
        lambda level: None
    )

    response = client.get("/api/quests/reward/99")

    data = response.get_json()

    assert response.status_code == 404
    assert data["success"] is False
    assert data["error"] == "Награда не найдена"