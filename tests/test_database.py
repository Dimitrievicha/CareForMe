@'


"""
Тесты базы данных CareForMe
Тестировщик: marishkkka
Ветка: first_test_db
"""

import pytest
import pymysql

# ============================================================
# КОНФИГУРАЦИЯ ПОДКЛЮЧЕНИЯ (ЗАМЕНИТЬ НА РЕАЛЬНЫЕ ДАННЫЕ)
# ============================================================
DB_CONFIG = {
    '\''
host
'\'': '\''
localhost
'\'',
'\''
port
'\'': 3306,
'\''
user
'\'': '\''
root
'\'',  # Уточнить у разработчика
'\''
password
'\'': '\'''\'',  # Уточнить у разработчика
'\''
database
'\'': '\''
Care_For_Me
'\'',
'\''
charset
'\'': '\''
utf8mb4
'\''
}

# ============================================================


class TestDatabaseConnection:
    """Класс тестов: Подключение к базе данных"""

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-01 - Проверка возможности подключения к БД
    # --------------------------------------------------------
    def test_tc01_can_connect_to_database(self):
        """TC-01: Проверка возможности подключения к БД"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()[0]
            conn.close()

            assert result == 1, "Запрос SELECT 1 не вернул 1"
        except Exception as e:
            pytest.fail(f"Не удалось подключиться к БД: {e}")


class TestTablesExist:
    """Класс тестов: Существование таблиц"""

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-02 - Проверка существования таблицы users
    # --------------------------------------------------------
    def test_tc02_table_users_exists(self):
        """TC-02: Проверка существования таблицы users"""
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert 'users' in tables, "Таблица 'users' не найдена в базе данных"

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-03 - Проверка существования таблицы user_plants
    # --------------------------------------------------------
    def test_tc03_table_user_plants_exists(self):
        """TC-03: Проверка существования таблицы user_plants"""
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert 'user_plants' in tables, "Таблица 'user_plants' не найдена"

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-04 - Проверка существования таблицы plant_templates
    # --------------------------------------------------------
    def test_tc04_table_plant_templates_exists(self):
        """TC-04: Проверка существования таблицы plant_templates"""
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert 'plant_templates' in tables, "Таблица 'plant_templates' не найдена"


class TestUsersTableStructure:
    """Класс тестов: Структура таблицы users"""

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-05 - Проверка колонок таблицы users
    # --------------------------------------------------------
    def test_tc05_users_table_has_required_columns(self):
        """TC-05: Проверка колонок таблицы users"""
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DESCRIBE users")
        columns = [row[0] for row in cursor.fetchall()]
        conn.close()

        required_columns = ['id', 'username', 'password_hash', 'created_at']
        for col in required_columns:
            assert col in columns, f"Колонка '{col}' отсутствует в таблице users"

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-06 - Проверка PRIMARY KEY в таблице users
    # --------------------------------------------------------
    def test_tc06_users_has_primary_key(self):
        """TC-06: Проверка PRIMARY KEY в таблице users"""
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW KEYS FROM users WHERE Key_name = '\''PRIMARY'\''")
        pk = cursor.fetchone()
        conn.close()

        assert pk is not None, "В таблице users отсутствует PRIMARY KEY"


class TestUserPlantsTableStructure:
    """Класс тестов: Структура таблицы user_plants"""

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-07 - Проверка колонок таблицы user_plants
    # --------------------------------------------------------
    def test_tc07_user_plants_has_required_columns(self):
        """TC-07: Проверка колонок таблицы user_plants"""
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DESCRIBE user_plants")
        columns = [row[0] for row in cursor.fetchall()]
        conn.close()

        required_columns = ['id', 'user_id', 'template_id', 'health_status', 'growth_stage', 'is_alive']
        for col in required_columns:
            assert col in columns, f"Колонка '{col}' отсутствует в таблице user_plants"


class TestRepositoriesImports:
    """Класс тестов: Импорт репозиториев"""

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-08 - Проверка импорта репозитория растений
    # --------------------------------------------------------
    def test_tc08_plant_repository_imports(self):
        """TC-08: Проверка импорта PlantRepository"""
        try:
            from src.backend.database_full.repository.plant_repository import PlantRepository
            assert PlantRepository is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать PlantRepository: {e}")

    # --------------------------------------------------------
    # ТЕСТ-КЕЙС: TC-09 - Проверка импорта репозитория пользователей
    # --------------------------------------------------------
    def test_tc09_user_repository_imports(self):
        """TC-09: Проверка импорта UserRepository"""
        try:
            from src.backend.database_full.repository.user_repository import UserRepository
            assert UserRepository is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать UserRepository: {e}")


'@ | Out-File -FilePath tests/test_database.py -Encoding utf8