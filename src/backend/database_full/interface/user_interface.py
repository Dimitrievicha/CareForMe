"""
Интерфейс для работы с пользователями (авторизация, профиль, дизайны).

Предоставляет внешний API для работы с пользователями:
    - регистрация и вход
    - управление сессиями
    - профиль и статистика
    - уровни и задания
    - дизайны (горшки, лейки)

"""

from typing import Dict, Any, Optional, List
from ..auth.auth_manager import auth_manager
from ..service.user_service import user_service
from ..service.level_quest_service import level_quest_service
from ..database.db_manager import get_db_manager


class UserInterface:
    """
    Интерфейс для работы с пользователями.

    Объединяет функционал:
        - Авторизация (auth_manager)
        - Профиль и статистика (user_service)
        - Уровневые задания (level_quest_service)

    Attributes:
        _auth (AuthManager): Менеджер авторизации
        _user_service (UserService): Сервис пользователя
        _quest_service (LevelQuestService): Сервис уровневых заданий
    """

    def __init__(self):
        """Инициализирует интерфейс со всеми сервисами."""
        self._auth = auth_manager
        self._user_service = user_service
        self._quest_service = level_quest_service
        self.db = get_db_manager()

    # В user_interface.py добавить:

    def complete_tutorial(self, user_id: str) -> bool:
        """Отметить обучение пройденным."""
        return self._user_service.complete_tutorial(user_id)

    def register(self, username: str, password: str) -> Dict[str, Any]:
        """
        Регистрация нового пользователя.

        Args:
            username: Имя пользователя (мин. 3 символа)
            password: Пароль (мин. 4 символа)

        Returns:
            Результат регистрации

        """
        return self._auth.register(username, password)

    def login(self, username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        """
        Вход пользователя.

        Args:
            username: Имя пользователя
            password: Пароль
            remember_me: Запомнить на 30 дней (иначе на 1 день)

        Returns:
            Результат авторизации с токеном сессии

        """
        return self._auth.login(username, password, remember_me)

    def logout(self, session_token: str) -> bool:
        """
        Выход пользователя (завершение сессии).

        Args:
            session_token: Токен сессии

        Returns:
            True если успешно
        """
        return self._auth.logout(session_token)

    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Проверить валидность сессии.

        Args:
            session_token: Токен сессии

        Returns:
            {"user_id": "...", "username": "..."} или None
        """
        return self._auth.verify_session(session_token)

    def get_current_user(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Получить текущего пользователя по токену.

        Args:
            session_token: Токен сессии

        Returns:
            Данные пользователя или None
        """
        return self._auth.verify_session(session_token)

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить игровой профиль пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Данные профиля
        """
        return self._user_service.get_profile(user_id)

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получить основную статистику пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Статистика (уровень, растения, поливы, серии)
        """
        return self._user_service.get_stats(user_id)

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить основную информацию о пользователе.

        Args:
            user_id: ID пользователя

        Returns:
            {"id": "...", "username": "...", "created_at": "...", "last_login": "...", "login_count": 0}
        """
        return self._auth.get_user(user_id)

    def get_level_info(self, user_id: str) -> Dict[str, Any]:
        """
        Получить информацию об уровне пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Информация о текущем уровне и следующих заданиях
        """
        return self._user_service.get_level_info(user_id)

    def get_current_level(self, user_id: str) -> int:
        """
        Получить текущий уровень пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Уровень (1-5)
        """
        return self._user_service.get_current_level(user_id)

    def get_quests_status(self, user_id: str) -> Dict[int, Dict[str, Any]]:
        """
        Получить статус всех заданий для всех уровней.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь {уровень: статус}
        """
        return self._quest_service.get_all_quests_status(user_id)

    def check_quests(self, user_id: str) -> Dict[str, Any]:
        """
        Принудительно проверить выполнение заданий.

        Args:
            user_id: ID пользователя

        Returns:
            Результат проверки с информацией о повышении уровня
        """
        return self._quest_service.check_and_update_quests(user_id)

    def update_daily_streak(self, user_id: str) -> Dict[str, Any]:
        """
        Обновить серию дней подряд (вызывать при ежедневном входе).

        Args:
            user_id: ID пользователя

        Returns:
            Результат обновления серии
        """
        return self._user_service.update_daily_streak(user_id)

    def get_streak_info(self, user_id: str) -> Dict[str, int]:
        """
        Получить информацию о серии дней.

        Args:
            user_id: ID пользователя

        Returns:
            {"consecutive_days": 5, "best_streak": 10}
        """
        return self._user_service.get_streak_info(user_id)

    def get_plant_slots_info(self, user_id: str) -> Dict[str, int]:
        """
        Получить информацию о слотах для растений.

        Args:
            user_id: ID пользователя

        Returns:
            {"current": 2, "max": 5, "available": 3}
        """
        return self._user_service.get_plant_slots(user_id)

    def has_free_slot(self, user_id: str) -> bool:
        """
        Проверить, есть ли свободный слот для посадки.

        Args:
            user_id: ID пользователя

        Returns:
            True если есть свободный слот
        """
        return self._user_service.has_free_slot(user_id)

    def get_unlocked_pots(self, user_id: str) -> List[str]:
        """
        Получить список открытых горшков.

        Args:
            user_id: ID пользователя

        Returns:
            Список ID дизайнов горшков

        """
        return self._user_service.get_unlocked_pots(user_id)

    def get_unlocked_watering_cans(self, user_id: str) -> List[str]:
        """
        Получить список открытых леек.

        Args:
            user_id: ID пользователя

        Returns:
            Список ID дизайнов леек
        """
        return self._user_service.get_unlocked_watering_cans(user_id)

    def get_current_designs(self, user_id: str) -> Dict[str, str]:
        """
        Получить текущие выбранные дизайны.

        Args:
            user_id: ID пользователя

        Returns:
            {"pot": "standard", "watering_can": "standard"}
        """
        return self._user_service.get_current_designs(user_id)

    def change_pot(self, user_id: str, pot_id: str) -> Dict[str, Any]:
        """
        Сменить текущий горшок.

        Args:
            user_id: ID пользователя
            pot_id: ID дизайна горшка

        Returns:
            {"success": True} или {"success": False, "error": "..."}
        """
        return self._user_service.change_pot(user_id, pot_id)

    def change_watering_can(self, user_id: str, can_id: str) -> Dict[str, Any]:
        """
        Сменить текущую лейку.

        Args:
            user_id: ID пользователя
            can_id: ID дизайна лейки

        Returns:
            {"success": True} или {"success": False, "error": "..."}
        """
        return self._user_service.change_watering_can(user_id, can_id)

user_interface = UserInterface()


def register(username: str, password: str) -> Dict[str, Any]:
    """Быстрая функция регистрации."""
    return user_interface.register(username, password)


def login(username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
    """Быстрая функция входа."""
    return user_interface.login(username, password, remember_me)


def logout(session_token: str) -> bool:
    """Быстрая функция выхода."""
    return user_interface.logout(session_token)


def get_current_user(session_token: str) -> Optional[Dict[str, Any]]:
    """Быстрая функция получения текущего пользователя."""
    return user_interface.get_current_user(session_token)