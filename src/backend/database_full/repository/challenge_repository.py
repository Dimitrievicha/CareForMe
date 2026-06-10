"""
Репозиторий для работы TESTING_REPORT.md достижениями (ачивками).

Содержит методы для работы TESTING_REPORT.md таблицами:
    - achievements: справочник достижений
    - user_achievements: прогресс пользователей по достижениям

"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class ChallengeRepository(BaseRepository):
    """
    Репозиторий для таблиц achievements и user_achievements.

    Обрабатывает все операции TESTING_REPORT.md достижениями:
        - Получение списка достижений
        - Отслеживание прогресса
        - Отметка о выполнении
        - Проверка условий для ачивок
    """
    def get_all_achievements(self, only_active: bool = True) -> List[Dict[str, Any]]:
        """
        Получает все достижения из справочника.

        Args:
            only_active: Если True, только активные достижения

        Returns:
            Список достижений (БЕЗ монет и XP)

        Returns структура:
            [
                {
                    "id": "uuid-...",
                    "name": "Заботливый родитель",
                    "description": "Вырастить цветок от семечка до зрелости...",
                    "requirement_type": "grow_to_maturity_perfect",
                    "target_value": 1,
                    "sort_order": 1
                },
                ...
            ]
        """
        active_filter = "WHERE is_active = 1" if only_active else ""
        return self.db.execute_query(f"""
            SELECT id, name, description, requirement_type, target_value, sort_order
            FROM achievements {active_filter}
            ORDER BY sort_order
        """)

    def get_achievement_by_id(self, achievement_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает достижение по ID.

        Args:
            achievement_id: UUID достижения

        Returns:
            Данные достижения или None
        """
        return self.get_by_id("achievements", "id", achievement_id)

    def get_achievement_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Получает достижение по названию.

        Args:
            name: Название достижения

        Returns:
            Данные достижения или None

        """
        result = self.db.execute_query(
            "SELECT * FROM achievements WHERE name = ?",
            (name,)
        )
        return result[0] if result else None

    def get_user_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает достижения пользователя TESTING_REPORT.md текущим прогрессом.

        Args:
            user_id: ID пользователя

        Returns:
            Список достижений TESTING_REPORT.md прогрессом

        Returns структура:
            [
                {
                    "id": "...",
                    "name": "Заботливый родитель",
                    "current_progress": 0,  # текущий прогресс
                    "is_completed": 0,      # выполнено или нет
                    "completed_at": None,   # дата выполнения
                    ...
                },
                ...
            ]
        """
        return self.db.execute_query("""
            SELECT a.*, ua.current_progress, ua.is_completed, ua.completed_at
            FROM achievements a
            LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
            WHERE a.is_active = 1
            ORDER BY a.sort_order
        """, (user_id,))

    def get_completed_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает завершенные достижения пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список завершенных достижений TESTING_REPORT.md датами выполнения

        """
        return self.db.execute_query("""
            SELECT a.*, ua.completed_at
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ? AND ua.is_completed = 1
            ORDER BY ua.completed_at DESC
        """, (user_id,))

    def update_progress(self, user_id: str, achievement_id: str, progress: int) -> bool:
        """
        Обновляет прогресс достижения.

        Если записи не существует, создает новую.

        Args:
            user_id: ID пользователя
            achievement_id: UUID достижения
            progress: Текущий прогресс (число)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            INSERT INTO user_achievements (user_id, achievement_id, current_progress)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, achievement_id) DO UPDATE SET
                current_progress = excluded.current_progress
        """, (user_id, achievement_id, progress))

    def complete_achievement(self, user_id: str, achievement_id: str) -> bool:
        """
        Отмечает достижение как выполненное.

        Args:
            user_id: ID пользователя
            achievement_id: UUID достижения

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_achievements 
            SET is_completed = 1, completed_at = CURRENT_DATE
            WHERE user_id = ? AND achievement_id = ?
        """, (user_id, achievement_id))

    def is_achievement_completed(self, user_id: str, achievement_id: str) -> bool:
        """
        Проверяет, выполнено ли достижение.

        Args:
            user_id: ID пользователя
            achievement_id: UUID достижения

        Returns:
            True если выполнено
        """
        result = self.db.execute_query("""
            SELECT is_completed FROM user_achievements 
            WHERE user_id = ? AND achievement_id = ?
        """, (user_id, achievement_id))
        return result[0]['is_completed'] == 1 if result else False

    def check_grow_to_maturity_perfect(self, user_id: str) -> int:
        """
        Подсчитывает количество растений, выращенных до зрелости
        без критических ошибок (для ачивки "Заботливый родитель").

        Args:
            user_id: ID пользователя

        Returns:
            Количество "идеальных" растений (1 = ачивка выполнена)
        """
        result = self.db.execute_query("""
            SELECT COUNT(*) as count FROM user_plants 
            WHERE user_id = ? AND growth_stage = 'mature' 
            AND is_alive = 1 AND has_perfect_growth = 1
        """, (user_id,))
        return result[0]['count'] if result else 0

    def check_first_wither(self, user_id: str) -> int:
        """
        Проверяет, была ли первая смерть растения.

        Args:
            user_id: ID пользователя

        Returns:
            1 если хотя бы одно растение умерло, иначе 0
        """
        result = self.db.execute_query("""
            SELECT COUNT(*) as count FROM user_plants 
            WHERE user_id = ? AND is_alive = 0 AND times_reborn = 1
            LIMIT 1
        """, (user_id,))
        return 1 if (result and result[0]['count'] > 0) else 0

    def check_first_negative_effect(self, user_id: str) -> int:
        """
        Проверяет, был ли получен негативный эффект.

        Args:
            user_id: ID пользователя

        Returns:
            1 если была хотя бы одна ошибка, иначе 0
        """
        result = self.db.execute_query("""
            SELECT COUNT(*) as count FROM user_mistakes 
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,))
        return 1 if (result and result[0]['count'] > 0) else 0

    def check_species_collected(self, user_id: str) -> int:
        """
        Подсчитывает количество собранных видов растений.

        Args:
            user_id: ID пользователя

        Returns:
            Количество уникальных видов (максимум 3)
        """
        result = self.db.execute_query("""
            SELECT COUNT(DISTINCT template_id) as count FROM user_plants 
            WHERE user_id = ? AND growth_stage = 'mature' AND is_alive = 1
        """, (user_id,))
        return result[0]['count'] if result else 0

    def get_level(self, user_id: str) -> int:
        """
        Получает текущий уровень пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Уровень (по умолчанию 1)
        """
        result = self.db.execute_query(
            "SELECT current_level FROM player_profiles WHERE user_id = ?",
            (user_id,)
        )
        return result[0]['current_level'] if result else 1

    def get_consecutive_days(self, user_id: str) -> int:
        """
        Получает текущую серию дней подряд.

        Args:
            user_id: ID пользователя

        Returns:
            Количество дней подряд
        """
        result = self.db.execute_query(
            "SELECT consecutive_days FROM player_profiles WHERE user_id = ?",
            (user_id,)
        )
        return result[0]['consecutive_days'] if result else 0