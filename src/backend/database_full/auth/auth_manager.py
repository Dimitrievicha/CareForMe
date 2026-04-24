"""Модуль авторизации пользователей.

Обеспечивает регистрацию, вход, управление сессиями.
Использует хэширование паролей и токен-байased сессии.

Пример:
    >>> from auth.auth_manager import auth_manager
    >>> result = auth_manager.register("john", "secret123")
    >>> if result['success']:
    ...     print("Пользователь создан!")
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ..repository.user_repository import UserRepository


class AuthManager:
    """Менеджер авторизации.

    Обрабатывает регистрацию, логин, логаут и проверку сессий.

    Attributes:
        user_repo (UserRepository): Репозиторий пользователей
    """

    def __init__(self):
        """Инициализирует менеджер с репозиторием пользователей."""
        self.user_repo = UserRepository()

    def _hash_password(self, password: str) -> str:
        """Хэширует пароль с помощью SHA-256.

        :param password: Пароль в открытом виде
        :type password: str
        :return: Хэш пароля
        :rtype: str
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str) -> Dict[str, Any]:
        """Регистрирует нового пользователя.

        :param username: Имя пользователя (минимум 3 символа)
        :type username: str
        :param password: Пароль (минимум 4 символа)
        :type password: str
        :return: Результат регистрации
        :rtype: Dict[str, Any]

        :returns: Успех::
            {"success": True, "user_id": "uuid", "username": "john"}

        :returns: Ошибка::
            {"success": False, "error": "Пользователь уже существует"}

        :raises ValueError: Если имя или пароль слишком короткие
        """
        if self.user_repo.user_exists(username):
            return {"success": False, "error": "Пользователь уже существует"}

        if len(username) < 3:
            return {"success": False, "error": "Имя не менее 3 символов"}
        if len(password) < 4:
            return {"success": False, "error": "Пароль не менее 4 символов"}

        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)

        success = self.user_repo.create_user(user_id, username, password_hash)
        if not success:
            return {"success": False, "error": "Ошибка создания"}

        self.user_repo.create_profile(user_id, username)

        return {"success": True, "user_id": user_id, "username": username}

    def login(self, username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        """Авторизует пользователя и создает сессию.

        :param username: Имя пользователя
        :type username: str
        :param password: Пароль
        :type password: str
        :param remember_me: Если True, сессия будет активна 30 дней
        :type remember_me: bool
        :return: Результат авторизации с токеном сессии
        :rtype: Dict[str, Any]

        :returns: Успех::
            {
                "success": True,
                "user_id": "uuid",
                "username": "john",
                "session_token": "base64_token",
                "expires_at": "2024-01-01T00:00:00"
            }

        :returns: Ошибка::
            {"success": False, "error": "Неверный логин или пароль"}
        """
        user = self.user_repo.get_user_by_username(username)
        if not user or user['password_hash'] != self._hash_password(password):
            return {"success": False, "error": "Неверный логин или пароль"}

        self.user_repo.update_last_login(user['id'])

        session_token = secrets.token_urlsafe(32)
        expires_in_days = 30 if remember_me else 1
        expires_at = datetime.now() + timedelta(days=expires_in_days)

        self.user_repo.create_session(user['id'], session_token, expires_at.isoformat())

        return {
            "success": True,
            "user_id": user['id'],
            "username": user['username'],
            "session_token": session_token,
            "expires_at": expires_at.isoformat()
        }

    def logout(self, session_token: str) -> bool:
        """Завершает сессию пользователя.

        :param session_token: Токен сессии
        :type session_token: str
        :return: True если выход выполнен успешно
        :rtype: bool
        """
        return self.user_repo.revoke_session(session_token)

    def get_user_id_by_token(self, session_token: str) -> Optional[str]:
        """Получает ID пользователя по токену сессии.

        :param session_token: Токен сессии
        :type session_token: str
        :return: ID пользователя или None если сессия невалидна
        :rtype: Optional[str]
        """
        session = self.user_repo.get_session_by_token(session_token)
        if not session:
            return None

        expires_at = datetime.fromisoformat(session['expires_at'])
        if expires_at < datetime.now():
            return None

        return session['user_id']

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получает данные пользователя по ID.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Словарь с данными пользователя или None
        :rtype: Optional[Dict[str, Any]]
        """
        return self.user_repo.get_user_by_id(user_id)


# Глобальный экземпляр для удобства использования
auth_manager = AuthManager()