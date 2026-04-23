import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер для работы с БД через чистый SQL"""

    def __init__(self, db_path: str = "careforme.db"):
        self.db_path = db_path
        self._connection = None

    def connect(self) -> sqlite3.Connection:
        """Установка соединения с БД"""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def close(self):
        """Закрытие соединения"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        """Выполнение SELECT запроса"""
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
        """Выполнение INSERT/UPDATE/DELETE запроса"""
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
        """Выполнение массовой вставки"""
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
        """Получение ID последней вставленной записи"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT last_insert_rowid()")
        return cursor.fetchone()[0]

    def init_database_from_sql(self, sql_file_path: str) -> bool:
        """Инициализация БД из SQL файла"""
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
        """Проверка существования таблицы"""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.execute_query(query, (table_name,))
        return len(result) > 0 if result else False


_db_manager = None


def get_db_manager(db_path: str = "careforme.db") -> DatabaseManager:
    """Получение экземпляра DatabaseManager (синглтон)"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager