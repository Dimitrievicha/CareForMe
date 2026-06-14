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
    Не привязан к конкретной модели - работает со словарями.
    
    Attributes:
        db (DatabaseManager): Менеджер подключения к БД
    """

    def __init__(self):
        """
        Инициализирует репозиторий с подключением к БД.

        Args:
            db_path: Путь к файлу БД. Если не указан — используется синглтон,
                     который уже должен быть инициализирован в app.py.
        """
        self.db = get_db_manager()

    def get_by_id(self, table_name: str, id_column: str, id_value: str) -> Optional[Dict[str, Any]]:
        """
        Получает запись из таблицы по идентификатору.

        Args:
            table_name: Имя таблицы (например 'users', 'user_plants')
            id_column: Название колонки с ID (обычно 'id')
            id_value: Значение ID для поиска

        Returns:
            Словарь с данными записи или None, если не найдено
            
        Пример:
            >>> user = repo.get_by_id("users", "id", "abc-123")
            >>> print(user['username'])
        """
        result = self.db.execute_query(
            f"SELECT * FROM {table_name} WHERE {id_column} = ?",
            (id_value,)
        )
        return result[0] if result else None

    def get_by_field(self, table_name: str, field: str, value: Any) -> List[Dict[str, Any]]:
        """
        Получает записи по значению поля (может вернуть несколько).

        Args:
            table_name: Имя таблицы
            field: Название поля для фильтрации
            value: Значение для поиска

        Returns:
            Список записей, удовлетворяющих условию
            
        Пример:
            >>> plants = repo.get_by_field("user_plants", "user_id", user_id)
            >>> alive = [p for p in plants if p['is_alive']]
        """
        return self.db.execute_query(
            f"SELECT * FROM {table_name} WHERE {field} = ?",
            (value,)
        )

    def get_one_by_field(self, table_name: str, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        Получает первую запись по значению поля (для уникальных полей).

        Args:
            table_name: Имя таблицы
            field: Название поля (должно быть уникальным)
            value: Значение для поиска

        Returns:
            Первую найденную запись или None
            
        Пример:
            >>> user = repo.get_one_by_field("users", "username", "john")
        """
        results = self.get_by_field(table_name, field, value)
        return results[0] if results else None

    def insert(self, table: str, data: Dict[str, Any]) -> bool:
        """
        Вставляет новую запись в таблицу.

        Args:
            table_name: Имя таблицы
            data: Словарь {колонка: значение} для вставки

        Returns:
            True при успехе, False при ошибке
            
        Пример:
            >>> repo.insert("users", {
            ...     "id": "uuid",
            ...     "username": "john",
            ...     "password_hash": "..."
            ... })
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        return self.db.execute_update(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(data.values())
        )

    def update(self, table: str, id_column: str, id_value: str, data: Dict[str, Any]) -> bool:
        """
        Обновляет запись по ID.

        Args:
            table_name: Имя таблицы
            id_column: Название колонки с ID
            id_value: Значение ID
            data: Словарь {колонка: новое значение}

        Returns:
            True при успехе, False при ошибке
            
        Пример:
            >>> repo.update("users", "id", user_id, {"login_count": 5})
        """
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        values = list(data.values()) + [id_value]
        return self.db.execute_update(
            f"UPDATE {table} SET {set_clause} WHERE {id_column} = ?",
            tuple(values)
        )

    def count(self, table: str, where_clause: str = "", params: tuple = ()) -> int:
        """
        Подсчитывает количество записей в таблице.

        Args:
            table_name: Имя таблицы
            where_clause: Условие WHERE (без слова WHERE), например "user_id = ?"
            params: Параметры для подстановки в условие

        Returns:
            Количество записей
            
        Пример:
            >>> alive_count = repo.count("user_plants", "user_id = ? AND is_alive = 1", (user_id,))
        """
        query = f"SELECT COUNT(*) as count FROM {table}"
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
    