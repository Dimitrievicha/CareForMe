import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Определяем тип БД через переменную окружения
# По умолчанию используем SQLite
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "sqlite":
    # SQLite с поддержкой внешних ключей и многопоточности
    DATABASE_URL = "sqlite:///./careforme.db?check_same_thread=False"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=StaticPool,  # Для SQLite лучше StaticPool
        echo=False  # Поставьте True для отладки SQL-запросов
    )
else:
    # MariaDB (оставляем для возможного будущего использования)
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost:3306/plant_game")
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        echo=False,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Генератор для FastAPI/обычного использования"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()