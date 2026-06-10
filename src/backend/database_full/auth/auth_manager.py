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
import json

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
        """Инициализирует менеджер TESTING_REPORT.md репозиторием пользователей."""
        self.user_repo = UserRepository()

    def _hash_password(self, password: str) -> str:
        """
        Хэширует пароль TESTING_REPORT.md помощью SHA-256.

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
            Dict TESTING_REPORT.md результатом операции

        Returns структура при успехе:
            {
                "success": True,
                "user_id": "uuid-...",
                "username": "john"
            }

        Returns структура при ошибке:
            {
                "success": False,
                "error": "Пользователь уже существует"
            }

        Example:
            >>> result = auth_manager.register("anna", "qwerty123")
            >>> if result['success']:
            ...     print(f"Добро пожаловать, {result['username']}!")
        """
        # Проверка на существующего пользователя
        if self.user_repo.user_exists(username):
            return {"success": False, "error": "Пользователь уже существует"}

        # Валидация длины
        if len(username) < 3:
            return {"success": False, "error": "Имя не менее 3 символов"}
        if len(password) < 4:
            return {"success": False, "error": "Пароль не менее 4 символов"}

        # Создание пользователя
        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)

        success = self.user_repo.create_user(user_id, username, password_hash)
        if not success:
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
            Dict TESTING_REPORT.md результатом авторизации и токеном сессии

        Returns структура при успехе:
            {
                "success": True,
                "user_id": "uuid-...",
                "username": "john",
                "session_token": "base64_token...",
                "expires_at": "2024-01-01T00:00:00"
            }

        Returns структура при ошибке:
            {
                "success": False,
                "error": "Неверный логин или пароль"
            }

        Example:
            >>> result = auth_manager.login("anna", "qwerty123", remember_me=True)
            >>> if result['success']:
            ...     # Сохраняем токен в cookie или localStorage
            ...     save_token(result['session_token'])
        """
        # Поиск пользователя
        user = self.user_repo.get_user_by_username(username)
        if not user or user['password_hash'] != self._hash_password(password):
            return {"success": False, "error": "Неверный логин или пароль"}

        # Обновляем время последнего входа
        self.user_repo.update_last_login(user['id'])

        # Создаем токен сессии
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
        expires_at = datetime.fromisoformat(session['expires_at'])
        if expires_at < datetime.now():
            return None

        return session['user_id']

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные пользователя по ID.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь TESTING_REPORT.md данными пользователя или None

        Returns структура:
            {
                "id": "uuid-...",
                "username": "john",
                "created_at": "2024-01-01...",
                "last_login": "2024-01-02...",
                "login_count": 5
            }
        """
        return self.user_repo.get_user_by_id(user_id)

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает игровой профиль пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Данные профиля или None

        Returns структура:
            {
                "user_id": "uuid-...",
                "display_name": "john",
                "current_level": 2,
                "max_plants_slots": 2,
                "total_plants_grown": 3,
                "total_waterings": 15,
                "total_mistakes": 2,
                "total_deaths": 1,
                "current_plants_count": 2,
                "consecutive_days": 5,
                "best_streak": 5,
                "unlocked_pots": '["standard", "design_pot_1"]',
                "unlocked_watering_cans": '["standard"]',
                "current_pot": "standard",
                "current_watering_can": "standard"
            }
        """
        return self.user_repo.get_profile(user_id)

    def update_streak(self, user_id: str) -> Dict[str, Any]:
        """
        Обновляет ежедневную серию пользователя.

        Вызывается при каждом входе в игру.
        Если пользователь зашел сегодня - серия не меняется.
        Если зашел на следующий день - серия увеличивается.
        Если пропустил день - серия сбрасывается до 1.

        Args:
            user_id: ID пользователя

        Returns:
            Результат обновления серии

        Returns структура:
            {
                "success": True,
                "consecutive_days": 5,
                "best_streak": 7
            }

        Example:
            >>> # При входе пользователя
            >>> streak_info = auth_manager.update_streak(user_id)
            >>> print(f"Текущая серия: {streak_info['consecutive_days']} дней")
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"success": False}

        today = datetime.now().date()
        last_entry = datetime.fromisoformat(profile['last_entry']).date() if profile['last_entry'] else None

        # Если уже заходил сегодня
        if last_entry == today:
            return {"success": True, "consecutive_days": profile['consecutive_days'], "updated": False}

        # Проверяем, был ли вход вчера
        if last_entry and (today - last_entry).days == 1:
            new_streak = profile['consecutive_days'] + 1
        else:
            new_streak = 1  # Сброс серии

        best_streak = max(profile['best_streak'], new_streak)
        self.user_repo.update_streak(user_id, new_streak, best_streak)

        return {
            "success": True,
            "consecutive_days": new_streak,
            "best_streak": best_streak,
            "updated": True
        }

    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Проверяет валидность сессии и возвращает данные пользователя.

        Args:
            session_token: Токен сессии

        Returns:
            Dict TESTING_REPORT.md данными пользователя или None

        Returns структура:
            {
                "user_id": "uuid-...",
                "username": "john"
            }

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

        user = self.get_user(user_id)
        if not user:
            return None

        return {"user_id": user['id'], "username": user['username']}


# =====================================================
# Глобальный экземпляр для удобства использования
# =====================================================

auth_manager = AuthManager()