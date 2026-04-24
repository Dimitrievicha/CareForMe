"""Репозиторий для работы с достижениями.

Содержит методы для работы с таблицами:
    - achievements: справочник достижений
    - user_achievements: прогресс пользователей по достижениям

Пример:
    >>> repo = ChallengeRepository()
    >>> achievements = repo.get_user_achievements("user123")
    >>> for ach in achievements:
    ...     print(f"{ach['name']}: {ach['current_progress']}/{ach['target_value']}")
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class ChallengeRepository(BaseRepository):
    """Репозиторий для таблиц achievements и user_achievements."""

    # ==================== ACHIEVEMENTS ====================

    def get_all_achievements(self, only_active: bool = True) -> List[Dict[str, Any]]:
        """Получает все достижения.

        :param only_active: Если True, только активные достижения
        :type only_active: bool
        :return: Список достижений
        :rtype: List[Dict[str, Any]]
        """
        active_filter = "WHERE is_active = 1" if only_active else ""
        return self.db.execute_query(f"""
            SELECT id, name, description, requirement_type, target_value, 
                   reward_coins, reward_xp, sort_order
            FROM achievements {active_filter}
            ORDER BY sort_order
        """)

    def get_achievement_by_id(self, achievement_id: str) -> Optional[Dict[str, Any]]:
        """Получает достижение по ID.

        :param achievement_id: UUID достижения
        :type achievement_id: str
        :return: Данные достижения или None
        :rtype: Optional[Dict[str, Any]]
        """
        return self.get_by_id("achievements", "id", achievement_id)

    # ==================== USER ACHIEVEMENTS ====================

    def get_user_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Получает достижения пользователя с прогрессом.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Список достижений с прогрессом
        :rtype: List[Dict[str, Any]]
        """
        return self.db.execute_query("""
            SELECT a.*, ua.current_progress, ua.is_completed, ua.completed_at, ua.claimed
            FROM achievements a
            LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
            WHERE a.is_active = 1
            ORDER BY a.sort_order
        """, (user_id,))

    def get_completed_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Получает завершенные достижения пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Список завершенных достижений
        :rtype: List[Dict[str, Any]]
        """
        return self.db.execute_query("""
            SELECT a.*, ua.completed_at
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ? AND ua.is_completed = 1
            ORDER BY ua.completed_at DESC
        """, (user_id,))

    def get_unclaimed_rewards(self, user_id: str) -> List[Dict[str, Any]]:
        """Получает незабранные награды пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Список достижений с незабранными наградами
        :rtype: List[Dict[str, Any]]
        """
        return self.db.execute_query("""
            SELECT a.id, a.name, a.reward_coins, a.reward_xp
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ? AND ua.is_completed = 1 AND ua.claimed = 0
        """, (user_id,))

    def update_progress(self, user_id: str, achievement_id: str, progress: int) -> bool:
        """Обновляет прогресс достижения.

        :param user_id: ID пользователя
        :type user_id: str
        :param achievement_id: UUID достижения
        :type achievement_id: str
        :param progress: Текущий прогресс
        :type progress: int
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            INSERT INTO user_achievements (user_id, achievement_id, current_progress)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, achievement_id) DO UPDATE SET
                current_progress = excluded.current_progress
        """, (user_id, achievement_id, progress))

    def complete_achievement(self, user_id: str, achievement_id: str) -> bool:
        """Отмечает достижение как выполненное.

        :param user_id: ID пользователя
        :type user_id: str
        :param achievement_id: UUID достижения
        :type achievement_id: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE user_achievements 
            SET is_completed = 1, completed_at = CURRENT_DATE
            WHERE user_id = ? AND achievement_id = ?
        """, (user_id, achievement_id))

    def claim_reward(self, user_id: str, achievement_id: str) -> bool:
        """Отмечает награду как забранную.

        :param user_id: ID пользователя
        :type user_id: str
        :param achievement_id: UUID достижения
        :type achievement_id: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE user_achievements SET claimed = 1
            WHERE user_id = ? AND achievement_id = ?
        """, (user_id, achievement_id))

    def is_achievement_completed(self, user_id: str, achievement_id: str) -> bool:
        """Проверяет, выполнено ли достижение.

        :param user_id: ID пользователя
        :type user_id: str
        :param achievement_id: UUID достижения
        :type achievement_id: str
        :return: True если выполнено
        :rtype: bool
        """
        result = self.db.execute_query("""
            SELECT is_completed FROM user_achievements 
            WHERE user_id = ? AND achievement_id = ?
        """, (user_id, achievement_id))
        return result[0]['is_completed'] == 1 if result else False

    # ==================== CONDITION CHECKS ====================

    def check_grow_to_maturity(self, user_id: str) -> int:
        """Подсчитывает количество растений, выращенных до зрелости.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Количество зрелых растений
        :rtype: int
        """
        result = self.db.execute_query("""
            SELECT COUNT(*) as count FROM user_plants 
            WHERE user_id = ? AND growth_stage = 'mature' AND is_alive = 1
        """, (user_id,))
        return result[0]['count'] if result else 0

    def check_death_first(self, user_id: str) -> int:
        """Подсчитывает количество первых смертей растений.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Количество растений, умерших впервые
        :rtype: int
        """
        result = self.db.execute_query("""
            SELECT COUNT(*) as count FROM user_plants 
            WHERE user_id = ? AND is_alive = 0 AND times_reborn = 1
        """, (user_id,))
        return result[0]['count'] if result else 0

    def check_species_collected(self, user_id: str) -> int:
        """Подсчитывает количество собранных видов растений.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Количество уникальных видов
        :rtype: int
        """
        result = self.db.execute_query("""
            SELECT COUNT(DISTINCT template_id) as count FROM user_plants 
            WHERE user_id = ? AND is_alive = 1
        """, (user_id,))
        return result[0]['count'] if result else 0

    def get_level(self, user_id: str) -> int:
        """Получает уровень пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Уровень (по умолчанию 1)
        :rtype: int
        """
        result = self.db.execute_query(
            "SELECT level FROM player_profiles WHERE user_id = ?",
            (user_id,)
        )
        return result[0]['level'] if result else 1

    def get_consecutive_days(self, user_id: str) -> int:
        """Получает серию дней подряд.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Количество дней подряд
        :rtype: int
        """
        result = self.db.execute_query(
            "SELECT consecutive_days FROM player_profiles WHERE user_id = ?",
            (user_id,)
        )
        return result[0]['consecutive_days'] if result else 0