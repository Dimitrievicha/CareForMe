"""
Модуль управления подключением к SQLite базе данных.
Содержит класс DatabaseManager для работы с БД через чистый SQL.
Использует паттерн синглтон для глобального доступа.

"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

# Настройка логирования
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Менеджер для работы с БД через чистый SQL.

    Обеспечивает подключение к SQLite, выполнение запросов,
    массовые операции и инициализацию из SQL файла.

    Attributes:
        db_path (str): Путь к файлу базы данных
        _connection (sqlite3.Connection): Внутреннее соединение с БД
    """

    def __init__(self, db_path: str = "careforme.db"):
        """
        Инициализирует менеджер базы данных.

        Args:
            db_path: Путь к файлу SQLite БД. По умолчанию 'careforme.db'
        """
        self.db_path = db_path
        self._connection = None

    def connect(self) -> sqlite3.Connection:
        """
        Устанавливает соединение с базой данных.

        Если соединение уже существует, возвращает его.
        Включает поддержку внешних ключей и row_factory для словарей.

        Returns:
            Объект соединения SQLite
        """
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.isolation_level = None
            logger.info(f"Подключение к БД установлено: {self.db_path}")
        return self._connection

    def close(self):
        """
        Закрывает соединение с базой данных.

        Безопасно закрывает соединение, если оно открыто.
        """
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Соединение с БД закрыто")

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        """
        Выполняет SELECT запрос и возвращает результат.

        Args:
            query: SQL запрос (SELECT)
            params: Кортеж параметров для подстановки

        Returns:
            Список словарей с результатами или [] при ошибке

        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            # Преобразуем Row объекты в обычные словари
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            logger.error(f"Запрос: {query}")
            logger.error(f"Параметры: {params}")
            return []

    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """
        Выполняет INSERT/UPDATE/DELETE запрос.

        Args:
            query: SQL запрос (INSERT, UPDATE, DELETE)
            params: Кортеж параметров для подстановки

        Returns:
            True при успехе, False при ошибке

        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            # commit происходит автоматически благодаря isolation_level=None
            logger.debug(f"Запрос выполнен успешно: {query[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Ошибка выполнения обновления: {e}")
            logger.error(f"Запрос: {query}")
            logger.error(f"Параметры: {params}")
            return False

    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """
        Выполняет массовую вставку данных.

        Args:
            query: SQL запрос (обычно INSERT)
            params_list: Список кортежей параметров

        Returns:
            True при успехе, False при ошибке
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            # commit происходит автоматически
            logger.debug(f"Массовая вставка: {len(params_list)} записей")
            return True
        except Exception as e:
            logger.error(f"Ошибка массовой вставки: {e}")
            return False

    def get_last_insert_id(self) -> int:
        """
        Возвращает ID последней вставленной записи.

        Returns:
            Последний автоинкрементный ID

        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT last_insert_rowid()")
        return cursor.fetchone()[0]

    def init_database_from_sql(self, sql_file_path: str) -> bool:
        """
        Инициализирует БД, выполняя SQL скрипт из файла.

        Args:
            sql_file_path: Путь к SQL файлу с CREATE TABLE и INSERT

        Returns:
            True при успехе, False при ошибке

        """
        try:
            if not Path(sql_file_path).exists():
                raise FileNotFoundError(f"SQL файл не найден: {sql_file_path}")

            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            conn = self.connect()
            conn.executescript(sql_script)
            # commit происходит автоматически

            logger.info(f"БД успешно инициализирована из {sql_file_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            return False

    def table_exists(self, table_name: str) -> bool:
        """
        Проверяет существование таблицы в базе данных.

        Args:
            table_name: Имя таблицы для проверки

        Returns:
            True если таблица существует, иначе False
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.execute_query(query, (table_name,))
        return len(result) > 0 if result else False

    def begin_transaction(self):
        """Начинает транзакцию вручную (если нужно)."""
        conn = self.connect()
        conn.execute("BEGIN")

    def commit(self):
        """Фиксирует текущую транзакцию."""
        if self._connection:
            self._connection.commit()

    def rollback(self):
        """Откатывает текущую транзакцию."""
        if self._connection:
            self._connection.rollback()


_db_manager = None


def get_db_manager(db_path: str = None) -> DatabaseManager:
    """
    Возвращает глобальный экземпляр DatabaseManager (синглтон).

    Args:
        db_path: Путь к файлу БД. Используется ТОЛЬКО при первом вызове.
                 При последующих вызовах возвращается уже созданный синглтон.
                 Если None и синглтон ещё не создан — используется careforme.db.

    Returns:
        Единственный экземпляр DatabaseManager

    ВАЖНО: первый вызов должен быть в app.py с явным путём, ДО импорта
    репозиториев. Иначе синглтон создастся с путём None и упадёт.
    """
    global _db_manager
    if _db_manager is None:
        resolved = db_path or "careforme.db"
        _db_manager = DatabaseManager(resolved)
        logger.info(f"Создан глобальный экземпляр DatabaseManager: {resolved}")
    return _db_manager