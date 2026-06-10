"""
Автоматизированные тесты Auth API.

Проверяется:
- регистрация и вход пользователя;
- выход из системы;
- проверка авторизации;
- доступ к защищённым маршрутам без токена.

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


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_check_user_empty_body(client):
    response = client.post("/api/auth/check_user", json={})

    assert response.status_code == 400
    assert response.get_json()["exists"] is False


def test_register_short_username(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "ab",
            "password": "1234"
        }
    )

    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Имя пользователя не менее 3 символов"


def test_register_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "123"
        }
    )

    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Пароль не менее 4 символов"


def test_login_wrong_credentials(client):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "unknown_user",
            "password": "wrong_password"
        }
    )

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Неверный логин или пароль"


def test_verify_without_token(client):
    response = client.get("/api/auth/verify")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Нет сессии"


def test_complete_tutorial_without_auth(client):
    response = client.post("/api/auth/complete_tutorial")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Необходима авторизация"


def test_check_streak_without_auth(client):
    response = client.get("/api/auth/check_streak")

    data = response.get_json()

    assert response.status_code == 401
    assert data["success"] is False
    assert data["error"] == "Необходима авторизация"


def test_logout_without_auth(client):
    response = client.post("/api/auth/logout")

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True