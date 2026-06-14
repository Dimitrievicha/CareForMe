"""
Модуль авторизации пользователей.

Обеспечивает регистрацию, вход, управление сессиями.
Использует хэширование паролей и токен-базированные сессии.

"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ..repository.user_repository import UserRepository


class AuthManager:
    """
    Менеджер авторизации.

    Обрабатывает регистрацию, логин, логаут и проверку сессий.
    В системе НЕТ монет и XP, только уровни и дизайны.

    Attributes:
        user_repo (UserRepository): Репозиторий пользователей
    """

    def __init__(self):
        """Инициализирует менеджер с репозиторием пользователей."""
        self.user_repo = UserRepository()

    def _hash_password(self, password: str) -> str:
        """
        Хэширует пароль с помощью SHA-256.

        Args:
            password: Пароль в открытом виде

        Returns:
            Хэш пароля в виде hex-строки

        Note:
            В production рекомендуется использовать bcrypt или PBKDF2
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str) -> Dict[str, Any]:
        """
        Регистрирует нового пользователя.

        Args:
            username: Имя пользователя (минимум 3 символа)
            password: Пароль (минимум 4 символа)

        Returns:
            {"success": True, "user_id": str, "username": str}

            {"success": False, "error": str}

        Example:
            >>> result = auth_manager.register("anna", "qwerty123")
            >>> if result['success']:
            ...     print(f"Добро пожаловать, {result['username']}!")
        """
        if len(username) < 3:
            return {"success": False, "error": "Имя не менее 3 символов"}
        if len(password) < 4:
            return {"success": False, "error": "Пароль не менее 4 символов"}
        # Проверка на существующего пользователя
        if self.user_repo.user_exists(username):
            return {"success": False, "error": "Пользователь уже существует"}

       
        # Создание пользователя
        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)

        if not self.user_repo.create_user(user_id, username, password_hash):
            return {"success": False, "error": "Ошибка создания пользователя"}

        # Создание игрового профиля
        self.user_repo.create_profile(user_id, username)

        return {"success": True, "user_id": user_id, "username": username}

    def login(self, username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        """
        Авторизует пользователя и создает сессию.

        Args:
            username: Имя пользователя
            password: Пароль
            remember_me: Если True, сессия будет активна 30 дней

        Returns:
            {"success": True, "user_id": str, "username": str,
             "session_token": str, "expires_at": str}
            {"success": False, "error": str}

        Example:
            >>> result = auth_manager.login("anna", "qwerty123", remember_me=True)
            >>> if result['success']:
            ...     # Сохраняем токен в cookie или localStorage
            ...     save_token(result['session_token'])
        """
        user = self.user_repo.get_user_by_username(username)
        if not user or user['password_hash'] != self._hash_password(password):
            return {"success": False, "error": "Неверный логин или пароль"}

        # Обновляем время последнего входа
        self.user_repo.update_last_login(user['id'])

        # Создаем токен сессии
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=30 if remember_me else 1)

        self.user_repo.create_session(user['id'], session_token, expires_at.isoformat())

        return {
            "success": True,
            "user_id": user['id'],
            "username": user['username'],
            "session_token": session_token,
            "expires_at": expires_at.isoformat()
        }

    def logout(self, session_token: str) -> bool:
        """
        Завершает сессию пользователя (выход).

        Args:
            session_token: Токен сессии

        Returns:
            True если выход выполнен успешно

        Example:
            >>> auth_manager.logout(current_token)
            True
        """
        return self.user_repo.revoke_session(session_token)
    
    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Проверяет валидность сессии и возвращает данные пользователя.

        Args:
            session_token: Токен сессии
             
        Returns:
            {"user_id": str, "username": str} или None

        Example:
            >>> user = auth_manager.verify_session(token)
            >>> if user:
            ...     # Пользователь авторизован
            ...     print(f"Привет, {user['username']}!")
            ... else:
            ...     # Нужно перенаправить на страницу входа
            ...     redirect_to_login()
        """
        user_id = self.get_user_id_by_token(session_token)
        if not user_id:
            return None

        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return None

        return {"user_id": user['id'], "username": user['username']} 

    def get_user_id_by_token(self, session_token: str) -> Optional[str]:
        """
        Получает ID пользователя по токену сессии.

        Args:
            session_token: Токен сессии

        Returns:
            ID пользователя или None если сессия невалидна или истекла

        Example:
            >>> user_id = auth_manager.get_user_id_by_token(token)
            >>> if user_id:
            ...     print(f"Пользователь авторизован: {user_id}")
        """
        session = self.user_repo.get_session_by_token(session_token)
        if not session:
            return None

        # Проверка на истечение срока
        if datetime.fromisoformat(session['expires_at']) < datetime.now():
            return None

        return session['user_id']

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные пользователя по ID.

        Args:
            user_id: ID пользователя
            
        Returns:
            {
            
                "id": "uuid-...",
                "username": "john",
                "created_at": "2024-01-01...",
                "last_login": "2024-01-02...",
                "login_count": 5
            } 
            или None

        """
        return self.user_repo.get_user_by_id(user_id)

# =====================================================
# Глобальный экземпляр для удобства использования
# =====================================================

auth_manager = AuthManager()