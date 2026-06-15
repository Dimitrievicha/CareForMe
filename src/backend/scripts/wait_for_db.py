# #!/usr/bin/env python3
# """
# Скрипт ожидания готовности базы данных
# Используется в Docker для последовательного запуска сервисов
# """

# import time
# import sys
# import os


# def wait_for_db():
#     """Ожидает готовности PostgreSQL"""

#     # Для SQLite - просто ждем
#     database_url = os.environ.get('DATABASE_URL', '')

#     if 'sqlite' in database_url:
#         print("Используется SQLite, ожидание не требуется")
#         return True

#     # Для PostgreSQL
#     if 'postgresql' in database_url:
#         try:
#             import psycopg2
#             from psycopg2 import OperationalError
#         except ImportError:
#             print("psycopg2 не установлен, пропускаем ожидание PostgreSQL")
#             return True

#         print("Ожидание подключения к PostgreSQL...")

#         max_retries = 30
#         retry_interval = 2

#         for i in range(max_retries):
#             try:
#                 conn = psycopg2.connect(database_url)
#                 conn.close()
#                 print("PostgreSQL готов!")
#                 return True
#             except OperationalError as e:
#                 print(f"Попытка {i + 1}/{max_retries}: {str(e)[:50]}...")
#                 time.sleep(retry_interval)

#         print("Не удалось подключиться к PostgreSQL")
#         return False

#     print("База данных готова")
#     return True


# if __name__ == "__main__":
#     if wait_for_db():
#         sys.exit(0)
#     else:
#         sys.exit(1)