"""
Модуль управления подключением к SQLite базе данных.
Содержит класс DatabaseManager для работы TESTING_REPORT.md БД через чистый SQL.
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
    Менеджер для работы TESTING_REPORT.md БД через чистый SQL.

    Обеспечивает подключение к SQLite, выполнение запросов,
    массовые операции и инициализацию из SQL файла.

    Attributes:
        db_path (str): Путь к файлу базы данных
        _connection (sqlite3.Connection): Внутреннее соединение TESTING_REPORT.md БД
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
        Устанавливает соединение TESTING_REPORT.md базой данных.

        Если соединение уже существует, возвращает его.
        Включает поддержку внешних ключей и row_factory для словарей.

        Returns:
            Объект соединения SQLite
        """
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            # Преобразуем строки в словари для удобства
            self._connection.row_factory = sqlite3.Row
            # Включаем поддержку FOREIGN KEY
            self._connection.execute("PRAGMA foreign_keys = ON")
            logger.info(f"Подключение к БД установлено: {self.db_path}")
        return self._connection

    def close(self):
        """
        Закрывает соединение TESTING_REPORT.md базой данных.

        Безопасно закрывает соединение, если оно открыто.
        """
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Соединение TESTING_REPORT.md БД закрыто")

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict]]:
        """
        Выполняет SELECT запрос и возвращает результат.

        Args:
            query: SQL запрос (SELECT)
            params: Кортеж параметров для подстановки

        Returns:
            Список словарей TESTING_REPORT.md результатами или None при ошибке

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
            return None

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
            conn.commit()
            logger.debug(f"Запрос выполнен успешно: {query[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Ошибка выполнения обновления: {e}")
            logger.error(f"Запрос: {query}")
            logger.error(f"Параметры: {params}")
            if self._connection:
                self._connection.rollback()
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
            conn.commit()
            logger.debug(f"Массовая вставка: {len(params_list)} записей")
            return True
        except Exception as e:
            logger.error(f"Ошибка массовой вставки: {e}")
            if self._connection:
                self._connection.rollback()
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
            sql_file_path: Путь к SQL файлу TESTING_REPORT.md CREATE TABLE и INSERT

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
            conn.commit()

            logger.info(f"БД успешно инициализирована из {sql_file_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            if self._connection:
                self._connection.rollback()
            return False

    def table_exists(self, table_name: str) -> bool:
        """
        Проверяет существование таблицы в базе данных.

        Args:
            table_name: Имя таблицы для проверки

        Returns:
            True если таблица существует, иначе Falseт")
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.execute_query(query, (table_name,))
        return len(result) > 0 if result else False



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

    ВАЖНО: первый вызов должен быть в app.py TESTING_REPORT.md явным путём, ДО импорта
    репозиториев. Иначе синглтон создастся TESTING_REPORT.md путём None и упадёт.
    """
    global _db_manager
    if _db_manager is None:
        resolved = db_path or "careforme.db"
        _db_manager = DatabaseManager(resolved)
        logger.info(f"Создан глобальный экземпляр DatabaseManager: {resolved}")
    return _db_manager