"""Модуль управления подключением к SQLite базе данных.

Содержит класс DatabaseManager для работы с БД через чистый SQL.
Использует паттерн синглтон для глобального доступа.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер для работы с БД через чистый SQL.

    Обеспечивает подключение к SQLite, выполнение запросов,
    массовые операции и инициализацию из SQL файла.

    Attributes:
        db_path (str): Путь к файлу базы данных
        _connection (sqlite3.Connection): Внутреннее соединение с БД
    """

    def __init__(self, db_path: str = "careforme.db"):
        """Инициализирует менеджер базы данных.

        :param db_path: Путь к файлу SQLite БД. По умолчанию 'careforme.db'
        :type db_path: str
        """
        self.db_path = db_path
        self._connection = None

    def connect(self) -> sqlite3.Connection:
        """Устанавливает соединение с базой данных.

        Если соединение уже существует, возвращает его.
        Включает поддержку внешних ключей и row_factory для словарей.

        :return: Объект соединения SQLite
        :rtype: sqlite3.Connection

        :example:
            >>> db = DatabaseManager()
            >>> conn = db.connect()
        """
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def close(self):
        """Закрывает соединение с базой данных.

        Безопасно закрывает соединение, если оно открыто.
        """
        if self._connection:
            self._connection.close()
            self._connection = None

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        """Выполняет SELECT запрос и возвращает результат.

        :param query: SQL запрос (SELECT)
        :type query: str
        :param params: Кортеж параметров для подстановки
        :type params: tuple
        :return: Список словарей с результатами или None при ошибке
        :rtype: Optional[List[Dict]]

        :example:
            >>> db = DatabaseManager()
            >>> users = db.execute_query("SELECT * FROM users WHERE id = ?", ("123",))
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            logger.error(f"Запрос: {query}")
            return None

    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """Выполняет INSERT/UPDATE/DELETE запрос.

        :param query: SQL запрос (INSERT, UPDATE, DELETE)
        :type query: str
        :param params: Кортеж параметров для подстановки
        :type params: tuple
        :return: True при успехе, False при ошибке
        :rtype: bool

        :example:
            >>> db = DatabaseManager()
            >>> success = db.execute_update(
            ...     "UPDATE users SET login_count = login_count + 1 WHERE id = ?",
            ...     ("123",)
            ... )
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка выполнения обновления: {e}")
            logger.error(f"Запрос: {query}")
            if self._connection:
                self._connection.rollback()
            return False

    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """Выполняет массовую вставку данных.

        :param query: SQL запрос (обычно INSERT)
        :type query: str
        :param params_list: Список кортежей параметров
        :type params_list: List[tuple]
        :return: True при успехе, False при ошибке
        :rtype: bool

        :example:
            >>> db = DatabaseManager()
            >>> data = [("user1",), ("user2",)]
            >>> db.execute_many("INSERT INTO temp (name) VALUES (?)", data)
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка массовой вставки: {e}")
            if self._connection:
                self._connection.rollback()
            return False

    def get_last_insert_id(self) -> int:
        """Возвращает ID последней вставленной записи.

        :return: Последний автоинкрементный ID
        :rtype: int
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT last_insert_rowid()")
        return cursor.fetchone()[0]

    def init_database_from_sql(self, sql_file_path: str) -> bool:
        """Инициализирует БД, выполняя SQL скрипт из файла.

        :param sql_file_path: Путь к SQL файлу с CREATE TABLE и INSERT
        :type sql_file_path: str
        :return: True при успехе, False при ошибке
        :rtype: bool
        """
        try:
            if not Path(sql_file_path).exists():
                raise FileNotFoundError(f"SQL файл не найден: {sql_file_path}")

            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            conn = self.connect()
            conn.executescript(sql_script)
            conn.commit()

            logger.info(f"БД успешно инициализирована из {sql_file_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            if self._connection:
                self._connection.rollback()
            return False

    def table_exists(self, table_name: str) -> bool:
        """Проверяет существование таблицы в базе данных.

        :param table_name: Имя таблицы для проверки
        :type table_name: str
        :return: True если таблица существует, иначе False
        :rtype: bool
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.execute_query(query, (table_name,))
        return len(result) > 0 if result else False


_db_manager = None


def get_db_manager(db_path: str = "careforme.db") -> DatabaseManager:
    """Возвращает глобальный экземпляр DatabaseManager (синглтон).

    :param db_path: Путь к файлу БД. Используется только при первом вызове
    :type db_path: str
    :return: Единственный экземпляр DatabaseManager
    :rtype: DatabaseManager

    :example:
        >>> db = get_db_manager()
        >>> db2 = get_db_manager()
        >>> db is db2
        True
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager