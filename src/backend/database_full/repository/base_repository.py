"""Базовый репозиторий с общими методами для всех таблиц.

Предоставляет базовые CRUD операции для всех репозиториев.
Все конкретные репозитории наследуются от этого класса.

Пример:
    >>> class UserRepository(BaseRepository):
    ...     def get_by_username(self, username):
    ...         return self.get_by_id("users", "username", username)
"""

from typing import Optional, List, Dict, Any
from ..database.db_manager import get_db_manager


class BaseRepository:
    """Базовый класс для всех репозиториев.

    Содержит общие методы для работы с любой таблицей.

    Attributes:
        db (DatabaseManager): Менеджер подключения к БД
    """

    def __init__(self, db_path: str = None):
        """Инициализирует репозиторий с подключением к БД.

        :param db_path: Путь к файлу БД (опционально)
        :type db_path: str, optional
        """
        self.db = get_db_manager(db_path)

    def get_by_id(self, table_name: str, id_column: str, id_value: str) -> Optional[Dict[str, Any]]:
        """Получает запись из таблицы по идентификатору.

        :param table_name: Имя таблицы
        :type table_name: str
        :param id_column: Название колонки с ID
        :type id_column: str
        :param id_value: Значение ID
        :type id_value: str
        :return: Словарь с данными записи или None
        :rtype: Optional[Dict[str, Any]]

        :example:
            >>> repo = BaseRepository()
            >>> user = repo.get_by_id("users", "id", "123")
        """
        result = self.db.execute_query(
            f"SELECT * FROM {table_name} WHERE {id_column} = ?",
            (id_value,)
        )
        return result[0] if result else None

    def get_all(self, table_name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает все записи из таблицы с пагинацией.

        :param table_name: Имя таблицы
        :type table_name: str
        :param limit: Максимальное количество записей
        :type limit: int
        :param offset: Смещение (сколько пропустить)
        :type offset: int
        :return: Список словарей с записями
        :rtype: List[Dict[str, Any]]
        """
        return self.db.execute_query(
            f"SELECT * FROM {table_name} LIMIT ? OFFSET ?",
            (limit, offset)
        )

    def delete_by_id(self, table_name: str, id_column: str, id_value: str) -> bool:
        """Удаляет запись из таблицы по ID.

        :param table_name: Имя таблицы
        :type table_name: str
        :param id_column: Название колонки с ID
        :type id_column: str
        :param id_value: Значение ID
        :type id_value: str
        :return: True если удаление успешно, иначе False
        :rtype: bool
        """
        return self.db.execute_update(
            f"DELETE FROM {table_name} WHERE {id_column} = ?",
            (id_value,)
        )

    def count(self, table_name: str, where_clause: str = "", params: tuple = ()) -> int:
        """Подсчитывает количество записей в таблице.

        :param table_name: Имя таблицы
        :type table_name: str
        :param where_clause: Условие WHERE (без слова WHERE)
        :type where_clause: str
        :param params: Параметры для подстановки
        :type params: tuple
        :return: Количество записей
        :rtype: int

        :example:
            >>> repo = BaseRepository()
            >>> count = repo.count("users", "level > ?", (5,))
        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        result = self.db.execute_query(query, params)
        return result[0]['count'] if result else 0