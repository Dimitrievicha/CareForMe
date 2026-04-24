"""Репозиторий для работы с пользователями и профилями.

Содержит методы для работы с таблицами:
    - users: учетные записи пользователей
    - sessions: сессии входа
    - player_profiles: игровые профили

Пример:
    >>> repo = UserRepository()
    >>> user = repo.get_user_by_id("123")
    >>> print(user['username'])
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Репозиторий для таблиц users и player_profiles."""

    # ==================== USERS ====================

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Словарь с данными пользователя или None
        :rtype: Optional[Dict[str, Any]]
        """
        return self.get_by_id("users", "id", user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получает пользователя по имени.

        :param username: Имя пользователя
        :type username: str
        :return: Словарь с данными пользователя или None
        :rtype: Optional[Dict[str, Any]]
        """
        result = self.db.execute_query(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        return result[0] if result else None

    def create_user(self, user_id: str, username: str, password_hash: str) -> bool:
        """Создает нового пользователя.

        :param user_id: UUID пользователя
        :type user_id: str
        :param username: Имя пользователя
        :type username: str
        :param password_hash: Хэш пароля
        :type password_hash: str
        :return: True при успехе, False при ошибке
        :rtype: bool
        """
        return self.db.execute_update("""
            INSERT INTO users (id, username, password_hash)
            VALUES (?, ?, ?)
        """, (user_id, username, password_hash))

    def update_last_login(self, user_id: str) -> bool:
        """Обновляет время последнего входа и счетчик входов.

        :param user_id: ID пользователя
        :type user_id: str
        :return: True при успехе, False при ошибке
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP, login_count = login_count + 1
            WHERE id = ?
        """, (user_id,))

    def user_exists(self, username: str) -> bool:
        """Проверяет существование пользователя с таким именем.

        :param username: Имя пользователя
        :type username: str
        :return: True если пользователь существует
        :rtype: bool
        """
        return self.count("users", "username = ?", (username,)) > 0

    # ==================== SESSIONS ====================

    def create_session(self, user_id: str, token: str, expires_at: str) -> bool:
        """Создает новую сессию для пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param token: Уникальный токен сессии
        :type token: str
        :param expires_at: Дата истечения в ISO формате
        :type expires_at: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, token, expires_at))

    def get_session_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Получает сессию по токену (только активные).

        :param token: Токен сессии
        :type token: str
        :return: Данные сессии или None
        :rtype: Optional[Dict[str, Any]]
        """
        result = self.db.execute_query(
            "SELECT * FROM sessions WHERE token = ? AND is_revoked = 0",
            (token,)
        )
        return result[0] if result else None

    def revoke_session(self, token: str) -> bool:
        """Отзывает (завершает) сессию.

        :param token: Токен сессии
        :type token: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update(
            "UPDATE sessions SET is_revoked = 1 WHERE token = ?",
            (token,)
        )

    def revoke_all_user_sessions(self, user_id: str, keep_token: str = None) -> bool:
        """Отзывает все сессии пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param keep_token: Токен, который нужно сохранить (опционально)
        :type keep_token: str, optional
        :return: True при успехе
        :rtype: bool
        """
        if keep_token:
            return self.db.execute_update("""
                UPDATE sessions SET is_revoked = 1 WHERE user_id = ? AND token != ?
            """, (user_id, keep_token))
        return self.db.execute_update(
            "UPDATE sessions SET is_revoked = 1 WHERE user_id = ?",
            (user_id,)
        )

    # ==================== PLAYER PROFILES ====================

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получает игровой профиль пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Данные профиля или None
        :rtype: Optional[Dict[str, Any]]

        :returns: Словарь с ключами:
            level, xp, coins, total_plants_grown, total_waterings,
            total_mistakes, total_deaths, current_plants_count,
            max_plants_slots, consecutive_days, best_streak
        """
        result = self.db.execute_query(
            "SELECT * FROM player_profiles WHERE user_id = ?",
            (user_id,)
        )
        return result[0] if result else None

    def create_profile(self, user_id: str, display_name: str = None) -> bool:
        """Создает игровой профиль для пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param display_name: Отображаемое имя (по умолчанию = username)
        :type display_name: str, optional
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            INSERT INTO player_profiles (user_id, display_name)
            VALUES (?, ?)
        """, (user_id, display_name))

    def update_xp(self, user_id: str, new_xp: int, new_level: int) -> bool:
        """Обновляет опыт и уровень пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param new_xp: Новое значение опыта
        :type new_xp: int
        :param new_level: Новый уровень
        :type new_level: int
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET xp = ?, level = ? WHERE user_id = ?
        """, (new_xp, new_level, user_id))

    def add_coins(self, user_id: str, amount: int) -> bool:
        """Добавляет монеты пользователю.

        :param user_id: ID пользователя
        :type user_id: str
        :param amount: Количество монет (может быть отрицательным)
        :type amount: int
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET coins = coins + ? WHERE user_id = ?
        """, (amount, user_id))

    def remove_coins(self, user_id: str, amount: int) -> bool:
        """Списывает монеты (если достаточно).

        :param user_id: ID пользователя
        :type user_id: str
        :param amount: Количество монет для списания
        :type amount: int
        :return: True если списано, False если недостаточно монет
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET coins = coins - ? WHERE user_id = ? AND coins >= ?
        """, (amount, user_id, amount))

    def update_streak(self, user_id: str, consecutive_days: int, best_streak: int) -> bool:
        """Обновляет серию дней подряд.

        :param user_id: ID пользователя
        :type user_id: str
        :param consecutive_days: Текущая серия дней
        :type consecutive_days: int
        :param best_streak: Лучшая серия
        :type best_streak: int
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE player_profiles 
            SET last_entry = CURRENT_DATE, consecutive_days = ?, best_streak = ?
            WHERE user_id = ?
        """, (consecutive_days, best_streak, user_id))

    def update_plant_slots(self, user_id: str, delta: int) -> bool:
        """Изменяет количество слотов для растений.

        :param user_id: ID пользователя
        :type user_id: str
        :param delta: На сколько изменить (1 = +1 слот, -1 = -1 слот)
        :type delta: int
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET max_plants_slots = max_plants_slots + ? WHERE user_id = ?
        """, (delta, user_id))

    def update_current_plants_count(self, user_id: str, delta: int) -> bool:
        """Изменяет количество текущих растений.

        :param user_id: ID пользователя
        :type user_id: str
        :param delta: На сколько изменить (+1 при посадке, -1 при смерти)
        :type delta: int
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET current_plants_count = current_plants_count + ? WHERE user_id = ?
        """, (delta, user_id))

    def increment_stat(self, user_id: str, stat_name: str, delta: int = 1) -> bool:
        """Увеличивает статистику пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param stat_name: Название статистики (total_plants_grown, total_waterings,
                         total_mistakes, total_deaths)
        :type stat_name: str
        :param delta: На сколько увеличить (по умолчанию 1)
        :type delta: int
        :return: True при успехе, False если stat_name некорректен
        :rtype: bool
        """
        allowed_stats = ['total_plants_grown', 'total_waterings', 'total_mistakes', 'total_deaths']
        if stat_name not in allowed_stats:
            return False
        return self.db.execute_update(f"""
            UPDATE player_profiles SET {stat_name} = {stat_name} + ? WHERE user_id = ?
        """, (delta, user_id))

    def get_leaderboard(self, sort_by: str = "level", limit: int = 10) -> List[Dict[str, Any]]:
        """Получает таблицу лидеров.

        :param sort_by: Критерий сортировки (level, coins, total_plants_grown, consecutive_days)
        :type sort_by: str
        :param limit: Количество записей
        :type limit: int
        :return: Список лидеров
        :rtype: List[Dict[str, Any]]

        :example:
            >>> repo = UserRepository()
            >>> leaders = repo.get_leaderboard(sort_by="level", limit=5)
            >>> for leader in leaders:
            ...     print(f"{leader['username']}: {leader['level']} уровень")
        """
        valid_sort = ["level", "coins", "total_plants_grown", "consecutive_days"]
        if sort_by not in valid_sort:
            sort_by = "level"

        return self.db.execute_query(f"""
            SELECT u.username, p.level, p.xp, p.coins, p.total_plants_grown, 
                   p.consecutive_days, p.best_streak
            FROM player_profiles p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.{sort_by} DESC
            LIMIT ?
        """, (limit,))

    def complete_tutorial(self, user_id: str) -> bool:
        """Отмечает завершение туториала.

        :param user_id: ID пользователя
        :type user_id: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE player_profiles SET tutorial_completed = 1 WHERE user_id = ?
        """, (user_id,))