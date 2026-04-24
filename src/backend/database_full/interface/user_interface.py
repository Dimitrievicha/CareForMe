"""Интерфейс для работы с пользователями (авторизация и профиль).

Предоставляет внешний API для работы с пользователями:
    - регистрация и вход
    - управление сессиями
    - профиль и статистика
    - опыт и монеты
"""

from typing import Dict, Any, Optional
from ..auth.auth_manager import auth_manager


class UserInterface:
    """Интерфейс для работы с пользователями - связка между API и auth_manager.

    Все методы этого класса предназначены для вызова из внешнего кода.

    Attributes:
        _auth (AuthManager): Менеджер авторизации
    """

    def __init__(self):
        """Инициализирует интерфейс с менеджером авторизации."""
        self._auth = auth_manager

    # ==================== АВТОРИЗАЦИЯ ====================

    def register(self, username: str, password: str) -> Dict[str, Any]:
        """Регистрация нового пользователя.

        :param username: Имя пользователя (мин. 3 символа)
        :type username: str
        :param password: Пароль (мин. 4 символа)
        :type password: str
        :return: Результат регистрации
        :rtype: Dict[str, Any]

        :returns: Успех: {"success": True, "user_id": "...", "username": "..."}
        :returns: Ошибка: {"success": False, "error": "..."}

        :example:
            >>> interface = UserInterface()
            >>> result = interface.register("john", "secret123")
            >>> print(result['success'])
            True
        """
        return self._auth.register(username, password)

    def login(self, username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        """Вход пользователя.

        :param username: Имя пользователя
        :type username: str
        :param password: Пароль
        :type password: str
        :param remember_me: Запомнить на 30 дней (иначе на 1 день)
        :type remember_me: bool
        :return: Результат авторизации с токеном сессии
        :rtype: Dict[str, Any]

        :returns: Успех::
            {
                "success": True,
                "user_id": "...",
                "username": "...",
                "session_token": "...",
                "expires_at": "..."
            }
        :returns: Ошибка: {"success": False, "error": "..."}
        """
        return self._auth.login(username, password, remember_me)

    def logout(self, session_token: str) -> bool:
        """Выход пользователя (завершение сессии).

        :param session_token: Токен сессии
        :type session_token: str
        :return: True если успешно, False если ошибка
        :rtype: bool
        """
        return self._auth.logout(session_token)

    def logout_all_devices(self, user_id: str, current_token: str = None) -> int:
        """Выйти со всех устройств.

        :param user_id: ID пользователя
        :type user_id: str
        :param current_token: Текущий токен (его не трогаем)
        :type current_token: str, optional
        :return: Количество завершённых сессий
        :rtype: int
        """
        return self._auth.logout_all_devices(user_id, current_token)

    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Проверить валидность сессии.

        :param session_token: Токен сессии
        :type session_token: str
        :return: {"user_id": "...", "username": "..."} или None
        :rtype: Optional[Dict[str, Any]]
        """
        return self._auth.verify_session(session_token)

    def get_current_user(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Получить текущего пользователя по токену.

        :param session_token: Токен сессии
        :type session_token: str
        :return: Данные пользователя или None
        :rtype: Optional[Dict[str, Any]]
        """
        return self._auth.verify_session(session_token)

    # ==================== ПРОФИЛЬ ====================

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить игровой профиль пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Данные профиля или None
        :rtype: Optional[Dict[str, Any]]

        :returns::
            {
                "level": 1,
                "xp": 0,
                "coins": 0,
                "total_plants_grown": 0,
                "total_waterings": 0,
                "total_mistakes": 0,
                "total_deaths": 0,
                "current_plants_count": 0,
                "max_plants_slots": 1,
                "consecutive_days": 1,
                "best_streak": 1
            }
        """
        return self._auth.get_profile(user_id)

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить основную информацию о пользователе.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Данные пользователя или None
        :rtype: Optional[Dict[str, Any]]

        :returns: {"id": "...", "username": "...", "created_at": "...", "last_login": "...", "login_count": 0}
        """
        return self._auth.get_user(user_id)

    def get_full_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить полные данные пользователя (профиль + информация).

        :param user_id: ID пользователя
        :type user_id: str
        :return: Объединенные данные или None
        :rtype: Optional[Dict[str, Any]]

        :returns::
            {
                "user": {...},
                "profile": {...}
            }
        """
        user = self._auth.get_user(user_id)
        profile = self._auth.get_profile(user_id)

        if not user or not profile:
            return None

        return {
            "user": user,
            "profile": profile
        }

    # ==================== ОПЫТ И МОНЕТЫ ====================

    def add_xp(self, user_id: str, xp_amount: int) -> Dict[str, Any]:
        """Добавить опыт пользователю.

        :param user_id: ID пользователя
        :type user_id: str
        :param xp_amount: Количество опыта
        :type xp_amount: int
        :return: Результат начисления опыта
        :rtype: Dict[str, Any]

        :returns::
            {
                "success": True,
                "old_level": 1,
                "new_level": 2,
                "xp_gained": 100,
                "total_xp": 100,
                "leveled_up": True
            }
        """
        return self._auth.add_xp(user_id, xp_amount)

    def add_coins(self, user_id: str, coins_amount: int) -> bool:
        """Добавить монеты пользователю.

        :param user_id: ID пользователя
        :type user_id: str
        :param coins_amount: Количество монет
        :type coins_amount: int
        :return: True при успехе
        :rtype: bool
        """
        return self._auth.add_coins(user_id, coins_amount)

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Получить статистику пользователя (уровень, монеты, опыт).

        :param user_id: ID пользователя
        :type user_id: str
        :return: Словарь со статистикой
        :rtype: Dict[str, Any]

        :returns::
            {
                "level": 5,
                "xp": 250,
                "coins": 150,
                "next_level_xp": 500
            }
        """
        profile = self._auth.get_profile(user_id)
        if not profile:
            return {"level": 0, "xp": 0, "coins": 0, "next_level_xp": 100}

        next_level_xp = self._auth.db.execute_query(
            "SELECT required_xp FROM level_requirements WHERE level = ?",
            (profile['level'] + 1,)
        )
        next_level_xp = next_level_xp[0]['required_xp'] if next_level_xp else profile['xp'] + 100

        return {
            "level": profile['level'],
            "xp": profile['xp'],
            "coins": profile['coins'],
            "next_level_xp": next_level_xp
        }

    # ==================== СЕРИИ ====================

    def update_daily_streak(self, user_id: str) -> Dict[str, Any]:
        """Обновить серию дней подряд (вызывать при ежедневном входе).

        :param user_id: ID пользователя
        :type user_id: str
        :return: Результат обновления серии
        :rtype: Dict[str, Any]

        :returns::
            {
                "updated": True,
                "consecutive_days": 5,
                "best_streak": 5
            }
        """
        return self._auth.update_streak(user_id)

    def get_streak_info(self, user_id: str) -> Dict[str, Any]:
        """Получить информацию о серии дней.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Информация о серии
        :rtype: Dict[str, Any]

        :returns: {"consecutive_days": 5, "best_streak": 10}
        """
        profile = self._auth.get_profile(user_id)
        if not profile:
            return {"consecutive_days": 0, "best_streak": 0}

        return {
            "consecutive_days": profile['consecutive_days'],
            "best_streak": profile['best_streak']
        }

    # ==================== СЛОТЫ ====================

    def get_plant_slots_info(self, user_id: str) -> Dict[str, Any]:
        """Получить информацию о слотах для растений.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Информация о слотах
        :rtype: Dict[str, Any]

        :returns: {"current": 2, "max": 5, "available": 3}
        """
        profile = self._auth.get_profile(user_id)
        if not profile:
            return {"current": 0, "max": 1, "available": 1}

        return {
            "current": profile['current_plants_count'],
            "max": profile['max_plants_slots'],
            "available": profile['max_plants_slots'] - profile['current_plants_count']
        }


# Глобальный экземпляр для удобства
user_interface = UserInterface()


# Быстрые функции для прямого вызова
def register(username: str, password: str) -> Dict[str, Any]:
    """Быстрая функция регистрации.

    :param username: Имя пользователя
    :param password: Пароль
    :return: Результат регистрации
    """
    return user_interface.register(username, password)


def login(username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
    """Быстрая функция входа.

    :param username: Имя пользователя
    :param password: Пароль
    :param remember_me: Запомнить сессию
    :return: Результат входа
    """
    return user_interface.login(username, password, remember_me)


def logout(session_token: str) -> bool:
    """Быстрая функция выхода.

    :param session_token: Токен сессии
    :return: True при успехе
    """
    return user_interface.logout(session_token)


def get_current_user(session_token: str) -> Optional[Dict[str, Any]]:
    """Быстрая функция получения текущего пользователя.

    :param session_token: Токен сессии
    :return: Данные пользователя или None
    """
    return user_interface.get_current_user(session_token)