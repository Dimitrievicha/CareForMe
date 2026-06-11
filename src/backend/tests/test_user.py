"""
Автоматизированные тесты User API.

Проверяется:
- получение профиля пользователя;
- прохождение обучения;
- серия ежедневных входов;
- настройки громкости;
- смена дизайна горшка и лейки.

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
import web.user as user_module


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login_as_test_user(client):
    with client.session_transaction() as session:
        session["user_id"] = "test_user_id"


def test_get_profile_without_auth(client):
    response = client.get("/api/user/profile")
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_profile_not_found(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        user_module.user_interface,
        "get_profile",
        lambda user_id: None
    )

    response = client.get("/api/user/profile")
    data = response.get_json()

    assert response.status_code == 404
    assert data["success"] is False
    assert data["error"] == "Профиль не найден"


def test_get_profile_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        user_module.user_interface,
        "get_profile",
        lambda user_id: {
            "current_level": 2,
            "tutorial_completed": False
        }
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_user_info",
        lambda user_id: {"username": "test_user"}
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_unlocked_pots",
        lambda user_id: ["1", "2"]
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_unlocked_watering_cans",
        lambda user_id: ["1"]
    )

    response = client.get("/api/user/profile")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["profile"]["username"] == "test_user"
    assert data["profile"]["current_level"] == 2
    assert data["profile"]["unlocked_pots"] == ["1", "2"]
    assert data["profile"]["unlocked_watering_cans"] == ["1"]


def test_tutorial_done_without_auth(client):
    response = client.post("/api/user/tutorial_done")
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_tutorial_done_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        user_module.user_interface,
        "complete_tutorial",
        lambda user_id: True
    )

    response = client.post("/api/user/tutorial_done")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True


def test_get_streak_without_auth(client):
    response = client.get("/api/user/streak")
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_streak_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        user_module.user_interface,
        "get_streak_info",
        lambda user_id: {
            "consecutive_days": 5,
            "best_streak": 10
        }
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_profile",
        lambda user_id: {
            "last_entry": "2026-06-09"
        }
    )

    response = client.get("/api/user/streak")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["consecutive_days"] == 5
    assert data["best_streak"] == 10
    assert data["last_entry"] == "2026-06-09"


def test_set_volume_without_auth(client):
    response = client.post("/api/user/settings/volume", json={"volume": 50})
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_set_volume_success(client):
    login_as_test_user(client)

    response = client.post("/api/user/settings/volume", json={"volume": 70})
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["volume"] == 70


def test_set_volume_less_than_zero(client):
    login_as_test_user(client)

    response = client.post("/api/user/settings/volume", json={"volume": -10})
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["volume"] == 0


def test_set_volume_more_than_hundred(client):
    login_as_test_user(client)

    response = client.post("/api/user/settings/volume", json={"volume": 150})
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["volume"] == 100


def test_set_volume_invalid_value(client):
    login_as_test_user(client)

    response = client.post("/api/user/settings/volume", json={"volume": "abc"})
    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "volume должен быть числом 0–100"


def test_set_design_without_auth(client):
    response = client.post(
        "/api/user/settings/design",
        json={"type": "pot", "design_id": "1"}
    )
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_set_design_invalid_type(client):
    login_as_test_user(client)

    response = client.post(
        "/api/user/settings/design",
        json={"type": "hat", "design_id": "1"}
    )
    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "type должен быть pot или watering_can"


def test_set_design_empty_design_id(client):
    login_as_test_user(client)

    response = client.post(
        "/api/user/settings/design",
        json={"type": "pot", "design_id": ""}
    )
    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Укажите design_id"


def test_set_pot_design_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        user_module.user_interface,
        "change_pot",
        lambda user_id, design_id: {"success": True}
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_current_designs",
        lambda user_id: {
            "pot": "2",
            "watering_can": "1"
        }
    )

    response = client.post(
        "/api/user/settings/design",
        json={"type": "pot", "design_id": "2"}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["current_pot"] == "2"
    assert data["current_watering_can"] == "1"


def test_set_watering_can_design_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        user_module.user_interface,
        "change_watering_can",
        lambda user_id, design_id: {"success": True}
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_current_designs",
        lambda user_id: {
            "pot": "1",
            "watering_can": "2"
        }
    )

    response = client.post(
        "/api/user/settings/design",
        json={"type": "watering_can", "design_id": "2"}
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["current_pot"] == "1"
    assert data["current_watering_can"] == "2"


def test_set_design_interface_error(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        user_module.user_interface,
        "change_pot",
        lambda user_id, design_id: {
            "success": False,
            "error": "Дизайн не разблокирован"
        }
    )

    response = client.post(
        "/api/user/settings/design",
        json={"type": "pot", "design_id": "999"}
    )
    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Дизайн не разблокирован"


def test_get_designs_without_auth(client):
    response = client.get("/api/user/designs")
    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Не авторизован"


def test_get_designs_success(client, monkeypatch):
    login_as_test_user(client)

    monkeypatch.setattr(
        user_module.user_interface,
        "get_current_designs",
        lambda user_id: {
            "pot": "1",
            "watering_can": "1"
        }
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_unlocked_pots",
        lambda user_id: ["1"]
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_unlocked_watering_cans",
        lambda user_id: ["1"]
    )
    monkeypatch.setattr(
        user_module.user_interface,
        "get_profile",
        lambda user_id: {
            "current_level": 3
        }
    )

    response = client.get("/api/user/designs")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["current"] == {"pot": "1", "watering_can": "1"}
    assert data["unlocked_pots"] == ["1"]
    assert data["unlocked_cans"] == ["1"]
    assert data["user_level"] == 3
    assert len(data["all_pots"]) == 3
    assert len(data["all_cans"]) == 2