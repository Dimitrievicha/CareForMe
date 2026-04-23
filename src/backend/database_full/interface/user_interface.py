"""Интерфейс для работы с пользователями (авторизация и профиль)"""
from typing import Dict, Any, Optional
from ..auth.auth_manager import auth_manager


class UserInterface:
    """Интерфейс для работы с пользователями - связка между API и auth_manager"""

    def __init__(self):
        self._auth = auth_manager

    def register(self, username: str, password: str) -> Dict[str, Any]:
        """
        Регистрация нового пользователя

        Args:
            username: Имя пользователя (мин. 3 символа)
            password: Пароль (мин. 4 символа)

        Returns:
            {"success": True, "user_id": "...", "username": "..."}
            или {"success": False, "error": "..."}
        """
        return self._auth.register(username, password)

    def login(self, username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        """
        Вход пользователя

        Args:
            username: Имя пользователя
            password: Пароль
            remember_me: Запомнить на 30 дней (иначе на 1 день)

        Returns:
            {"success": True, "user_id": "...", "username": "...", "session_token": "...", "expires_at": "..."}
            или {"success": False, "error": "..."}
        """
        return self._auth.login(username, password, remember_me)

    def logout(self, session_token: str) -> bool:
        """
        Выход пользователя (завершение сессии)

        Args:
            session_token: Токен сессии

        Returns:
            True если успешно, False если ошибка
        """
        return self._auth.logout(session_token)

    def logout_all_devices(self, user_id: str, current_token: str = None) -> int:
        """
        Выйти со всех устройств

        Args:
            user_id: ID пользователя
            current_token: Текущий токен (его не трогаем)

        Returns:
            Количество завершённых сессий
        """
        return self._auth.logout_all_devices(user_id, current_token)

    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Проверить валидность сессии

        Args:
            session_token: Токен сессии

        Returns:
            {"user_id": "...", "username": "..."} или None
        """
        return self._auth.verify_session(session_token)

    def get_current_user(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Получить текущего пользователя по токену"""
        return self._auth.verify_session(session_token)

    # ==================== ПРОФИЛЬ ====================

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить игровой профиль пользователя

        Returns:
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
        """
        Получить основную информацию о пользователе

        Returns:
            {"id": "...", "username": "...", "created_at": "...", "last_login": "...", "login_count": 0}
        """
        return self._auth.get_user(user_id)

    def get_full_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить полные данные пользователя (профиль + информация)

        Returns:
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
        """
        Добавить опыт пользователю

        Returns:
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
        """Добавить монеты пользователю"""
        return self._auth.add_coins(user_id, coins_amount)

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Получить статистику пользователя (уровень, монеты, опыт)"""
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

    def update_daily_streak(self, user_id: str) -> Dict[str, Any]:
        """
        Обновить серию дней подряд (вызывать при ежедневном входе)

        Returns:
            {
                "updated": True,
                "consecutive_days": 5,
                "best_streak": 5
            }
        """
        return self._auth.update_streak(user_id)

    def get_streak_info(self, user_id: str) -> Dict[str, Any]:
        """Получить информацию о серии дней"""
        profile = self._auth.get_profile(user_id)
        if not profile:
            return {"consecutive_days": 0, "best_streak": 0}

        return {
            "consecutive_days": profile['consecutive_days'],
            "best_streak": profile['best_streak']
        }

    def get_plant_slots_info(self, user_id: str) -> Dict[str, Any]:
        """Получить информацию о слотах для растений"""
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


# Быстрые функции
def register(username: str, password: str) -> Dict[str, Any]:
    return user_interface.register(username, password)


def login(username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
    return user_interface.login(username, password, remember_me)


def logout(session_token: str) -> bool:
    return user_interface.logout(session_token)


def get_current_user(session_token: str) -> Optional[Dict[str, Any]]:
    return user_interface.get_current_user(session_token)