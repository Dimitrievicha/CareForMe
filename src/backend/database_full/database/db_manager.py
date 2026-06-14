"""
Модуль управления подключением к SQLite базе данных.
Содержит класс DatabaseManager для работы с БД через чистый SQL.
Использует паттерн синглтон для глобального доступа.

"""

import sqlite3
import logging
from typing import Optional, Dict, List

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
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        Устанавливает соединение с базой данных.

        Если соединение уже существует, возвращает его.
        Включает поддержку внешних ключей и row_factory для словарей.

        Returns:
            Объект соединения SQLite
        """
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, 
                check_same_thread=False, isolation_level=None)

            self._connection.row_factory = sqlite3.Row

            self._connection.execute("PRAGMA foreign_keys = ON")

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

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """
        Выполняет SELECT запрос и возвращает результат.

        Args:
            query: SQL запрос (SELECT)
            params: Кортеж параметров для подстановки

        Returns:
            Список словарей с результатами или [] при ошибке

        """
        try:
            cursor = self.connect().cursor()
            cursor.execute(query, params)
            # Преобразуем Row объекты в обычные словари
            return [dict(row) for row in cursor.fetchall()]
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
            self.connect().cursor().execute(query,params)
            logger.debug(f"Запрос выполнен: {query[:60]}...")
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
            self.connect().cursor().executemany(query,params_list)
            logger.debug(f"Массовая вставка: {len(params_list)} записей")
            return True
        except Exception as e:
            logger.error(f"Ошибка массовой вставки: {e}")
            return False


_db_manager: Optional[DatabaseManager] = None


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