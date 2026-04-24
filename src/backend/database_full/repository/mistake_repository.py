"""Репозиторий для работы с ошибками пользователей.

Содержит методы для работы с таблицей user_mistakes,
которая хранит историю ошибок для умных советов.

Пример:
    >>> repo = MistakeRepository()
    >>> repo.add_mistake("user123", "plant456", "overwater")
    >>> count = repo.get_mistakes_count("user123")
"""

from typing import List, Dict, Any
from .base_repository import BaseRepository


class MistakeRepository(BaseRepository):
    """Репозиторий для таблицы user_mistakes."""

    def add_mistake(self, user_id: str, plant_id: str, mistake_type: str, advice_shown: bool = False) -> bool:
        """Записывает ошибку пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param plant_id: ID растения
        :type plant_id: str
        :param mistake_type: Тип ошибки (overwater, drought, light, cold)
        :type mistake_type: str
        :param advice_shown: Был ли показан совет
        :type advice_shown: bool
        :return: True при успехе
        :rtype: bool

        :example:
            >>> repo = MistakeRepository()
            >>> repo.add_mistake("user123", "plant456", "overwater")
        """
        return self.db.execute_update("""
            INSERT INTO user_mistakes (user_id, plant_id, mistake_type, was_advice_shown)
            VALUES (?, ?, ?, ?)
        """, (user_id, plant_id, mistake_type, advice_shown))

    def get_mistakes_count(self, user_id: str, mistake_type: str = None) -> int:
        """Получает количество ошибок пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param mistake_type: Тип ошибки (опционально)
        :type mistake_type: str, optional
        :return: Количество ошибок
        :rtype: int

        :example:
            >>> repo = MistakeRepository()
            >>> total = repo.get_mistakes_count("user123")
            >>> overwater = repo.get_mistakes_count("user123", "overwater")
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
        """Получает все ошибки пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param limit: Максимальное количество записей
        :type limit: int
        :return: Список ошибок
        :rtype: List[Dict[str, Any]]
        """
        return self.db.execute_query("""
            SELECT * FROM user_mistakes 
            WHERE user_id = ? 
            ORDER BY occurred_at DESC
            LIMIT ?
        """, (user_id, limit))

    def get_plant_mistakes(self, plant_id: str) -> List[Dict[str, Any]]:
        """Получает ошибки для конкретного растения.

        :param plant_id: ID растения
        :type plant_id: str
        :return: Список ошибок для растения
        :rtype: List[Dict[str, Any]]
        """
        return self.db.execute_query("""
            SELECT * FROM user_mistakes 
            WHERE plant_id = ? 
            ORDER BY occurred_at DESC
        """, (plant_id,))

    def mark_advice_shown(self, mistake_id: int) -> bool:
        """Отмечает, что совет был показан для этой ошибки.

        :param mistake_id: ID записи об ошибке
        :type mistake_id: int
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE user_mistakes SET was_advice_shown = 1 WHERE id = ?
        """, (mistake_id,))

    def get_mistakes_by_type(self, user_id: str) -> Dict[str, int]:
        """Получает статистику ошибок по типам.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Словарь {тип_ошибки: количество}
        :rtype: Dict[str, int]

        :example:
            >>> repo = MistakeRepository()
            >>> stats = repo.get_mistakes_by_type("user123")
            >>> print(stats)
            {'overwater': 3, 'drought': 1, 'light': 2}
        """
        result = self.db.execute_query("""
            SELECT mistake_type, COUNT(*) as count
            FROM user_mistakes 
            WHERE user_id = ?
            GROUP BY mistake_type
        """, (user_id,))

        stats = {}
        for row in result:
            stats[row['mistake_type']] = row['count']
        return stats