"""
Базовый репозиторий с общими методами для всех таблиц.

Предоставляет базовые CRUD операции для всех репозиториев.
Все конкретные репозитории наследуются от этого класса.

"""

from typing import Optional, List, Dict, Any
from ..database.db_manager import get_db_manager


class BaseRepository:
    """
    Базовый класс для всех репозиториев.

    Содержит общие методы для работы с любой таблицей.

    Attributes:
        db (DatabaseManager): Менеджер подключения к БД

    """

    def __init__(self, db_path: str = None):
        """
        Инициализирует репозиторий с подключением к БД.

        Args:
            db_path: Путь к файлу БД (опционально, по умолчанию 'careforme.db')
        """
        self.db = get_db_manager(db_path)

    def get_by_id(self, table_name: str, id_column: str, id_value: str) -> Optional[Dict[str, Any]]:
        """
        Получает запись из таблицы по идентификатору.

        Args:
            table_name: Имя таблицы
            id_column: Название колонки с ID
            id_value: Значение ID

        Returns:
            Словарь с данными записи или None

        """
        result = self.db.execute_query(
            f"SELECT * FROM {table_name} WHERE {id_column} = ?",
            (id_value,)
        )
        return result[0] if result else None

    def get_all(self, table_name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Получает все записи из таблицы с пагинацией.

        Args:
            table_name: Имя таблицы
            limit: Максимальное количество записей
            offset: Смещение (сколько пропустить)

        Returns:
            Список словарей с записями

        """
        return self.db.execute_query(
            f"SELECT * FROM {table_name} LIMIT ? OFFSET ?",
            (limit, offset)
        )

    def delete_by_id(self, table_name: str, id_column: str, id_value: str) -> bool:
        """
        Удаляет запись из таблицы по ID.

        Args:
            table_name: Имя таблицы
            id_column: Название колонки с ID
            id_value: Значение ID

        Returns:
            True если удаление успешно, иначе False

        """
        return self.db.execute_update(
            f"DELETE FROM {table_name} WHERE {id_column} = ?",
            (id_value,)
        )

    def count(self, table_name: str, where_clause: str = "", params: tuple = ()) -> int:
        """
        Подсчитывает количество записей в таблице.

        Args:
            table_name: Имя таблицы
            where_clause: Условие WHERE (без слова WHERE)
            params: Параметры для подстановки

        Returns:
            Количество записей


        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        result = self.db.execute_query(query, params)
        return result[0]['count'] if result else 0

    def exists(self, table_name: str, where_clause: str, params: tuple = ()) -> bool:
        """
        Проверяет существование записи по условию.

        Args:
            table_name: Имя таблицы
            where_clause: Условие WHERE (без слова WHERE)
            params: Параметры для подстановки

        Returns:
            True если запись существует, иначе False

        """
        return self.count(table_name, where_clause, params) > 0