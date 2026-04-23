"""Базовый репозиторий с общими методами для всех таблиц"""
from typing import Optional, List, Dict, Any
from ..database.db_manager import get_db_manager


class BaseRepository:
    """Базовый класс для всех репозиториев"""

    def __init__(self, db_path: str = None):
        self.db = get_db_manager(db_path)

    def get_by_id(self, table_name: str, id_column: str, id_value: str) -> Optional[Dict[str, Any]]:
        """Получить запись по ID"""
        result = self.db.execute_query(
            f"SELECT * FROM {table_name} WHERE {id_column} = ?",
            (id_value,)
        )
        return result[0] if result else None

    def get_all(self, table_name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить все записи из таблицы"""
        return self.db.execute_query(
            f"SELECT * FROM {table_name} LIMIT ? OFFSET ?",
            (limit, offset)
        )

    def delete_by_id(self, table_name: str, id_column: str, id_value: str) -> bool:
        """Удалить запись по ID"""
        return self.db.execute_update(
            f"DELETE FROM {table_name} WHERE {id_column} = ?",
            (id_value,)
        )

    def count(self, table_name: str, where_clause: str = "", params: tuple = ()) -> int:
        """Получить количество записей"""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        result = self.db.execute_query(query, params)
        return result[0]['count'] if result else 0

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        """Выполнить произвольный SELECT запрос"""
        return self.db.execute_query(query, params)

    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """Выполнить произвольный UPDATE/INSERT/DELETE запрос"""
        return self.db.execute_update(query, params)