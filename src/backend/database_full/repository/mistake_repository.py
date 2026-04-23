"""Репозиторий для работы с ошибками пользователей"""
from typing import List, Dict, Any
from .base_repository import BaseRepository


class MistakeRepository(BaseRepository):
    """Репозиторий для таблицы user_mistakes"""

    def add_mistake(self, user_id: str, plant_id: str, mistake_type: str, advice_shown: bool = False) -> bool:
        """Записать ошибку пользователя"""
        return self.db.execute_update("""
            INSERT INTO user_mistakes (user_id, plant_id, mistake_type, was_advice_shown)
            VALUES (?, ?, ?, ?)
        """, (user_id, plant_id, mistake_type, advice_shown))

    def get_mistakes_count(self, user_id: str, mistake_type: str = None) -> int:
        """Получить количество ошибок"""
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
        """Получить все ошибки пользователя"""
        return self.db.execute_query("""
            SELECT * FROM user_mistakes 
            WHERE user_id = ? 
            ORDER BY occurred_at DESC
            LIMIT ?
        """, (user_id, limit))

    def get_plant_mistakes(self, plant_id: str) -> List[Dict[str, Any]]:
        """Получить ошибки для конкретного растения"""
        return self.db.execute_query("""
            SELECT * FROM user_mistakes 
            WHERE plant_id = ? 
            ORDER BY occurred_at DESC
        """, (plant_id,))

    def mark_advice_shown(self, mistake_id: int) -> bool:
        """Отметить, что совет был показан"""
        return self.db.execute_update("""
            UPDATE user_mistakes SET was_advice_shown = 1 WHERE id = ?
        """, (mistake_id,))

    def get_mistakes_by_type(self, user_id: str) -> Dict[str, int]:
        """Получить статистику ошибок по типам"""
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