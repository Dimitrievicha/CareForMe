"""
Репозиторий для работы TESTING_REPORT.md ошибками пользователей.

Содержит методы для работы TESTING_REPORT.md таблицей user_mistakes,
которая хранит историю ошибок для умных советов.

"""

from typing import List, Dict, Any
from .base_repository import BaseRepository


class MistakeRepository(BaseRepository):
    """
    Репозиторий для таблицы user_mistakes.

    Обрабатывает все операции TESTING_REPORT.md ошибками:
        - Запись ошибок
        - Получение статистики ошибок
        - Отслеживание показа советов
    """

    def add_mistake(self, user_id: str, plant_id: str, mistake_type: str, advice_shown: bool = False) -> bool:
        """
        Записывает ошибку пользователя.

        Args:
            user_id: ID пользователя
            plant_id: ID растения, TESTING_REPORT.md которым связана ошибка
            mistake_type: Тип ошибки
                - overwater: перелив
                - drought: засуха
                - light: неправильное освещение
                - cold: сквозняк/холод
            advice_shown: Был ли показан совет пользователю

        Returns:
            True при успехе

        """
        return self.db.execute_update("""
            INSERT INTO user_mistakes (user_id, plant_id, mistake_type, was_advice_shown)
            VALUES (?, ?, ?, ?)
        """, (user_id, plant_id, mistake_type, advice_shown))

    def get_mistakes_count(self, user_id: str, mistake_type: str = None) -> int:
        """
        Получает количество ошибок пользователя.

        Args:
            user_id: ID пользователя
            mistake_type: Тип ошибки (опционально, для фильтрации)

        Returns:
            Количество ошибок

        """
        if mistake_type:
            result = self.db.execute_query("""
                SELECT COUNT(*) as count FROM user_mistakes 
                WHERE user_id = ? AND mistake_type = ?
            """, (user_id, mistake_type))
        else:
            result = self.db.execute_query("""
                SELECT COUNT(*) as count FROM user_mistakes WHERE user_id = ?
            """, (user_id,))
        return result[0]['count'] if result else 0

    def get_user_mistakes(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получает список ошибок пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей

        Returns:
            Список ошибок, отсортированных от новых к старым

        """
        return self.db.execute_query("""
            SELECT * FROM user_mistakes 
            WHERE user_id = ? 
            ORDER BY occurred_at DESC
            LIMIT ?
        """, (user_id, limit))

    def get_plant_mistakes(self, plant_id: str) -> List[Dict[str, Any]]:
        """
        Получает ошибки для конкретного растения.

        Args:
            plant_id: ID растения

        Returns:
            Список ошибок для растения

        """
        return self.db.execute_query("""
            SELECT * FROM user_mistakes 
            WHERE plant_id = ? 
            ORDER BY occurred_at DESC
        """, (plant_id,))

    def mark_advice_shown(self, mistake_id: int) -> bool:
        """
        Отмечает, что совет был показан для этой ошибки.

        Args:
            mistake_id: ID записи об ошибке

        Returns:
            True при успехе

        """
        return self.db.execute_update("""
            UPDATE user_mistakes SET was_advice_shown = 1 WHERE id = ?
        """, (mistake_id,))

    def get_mistakes_by_type(self, user_id: str) -> Dict[str, int]:
        """
        Получает статистику ошибок по типам.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь {тип_ошибки: количество}
        """
        result = self.db.execute_query("""
            SELECT mistake_type, COUNT(*) as count
            FROM user_mistakes 
            WHERE user_id = ?
            GROUP BY mistake_type
        """, (user_id,))

        stats = {'overwater': 0, 'drought': 0, 'light': 0, 'cold': 0}
        for row in result:
            stats[row['mistake_type']] = row['count']
        return stats

    def get_today_mistakes(self, user_id: str) -> int:
        """
        Получает количество ошибок, сделанных сегодня.

        Args:
            user_id: ID пользователя

        Returns:
            Количество ошибок за сегодня

        """
        result = self.db.execute_query("""
            SELECT COUNT(*) as count FROM user_mistakes 
            WHERE user_id = ? AND DATE(occurred_at) = DATE('now')
        """, (user_id,))
        return result[0]['count'] if result else 0