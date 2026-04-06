import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Формат: mysql+pymysql://user:pass@host:port/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost:3306/plant_game")

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # аналог maximumPoolSize
    max_overflow=20,       # аналог maximumIdle (динамически)
    pool_timeout=30,       # connectionTimeout / 1000
    pool_recycle=1800,     # maxLifetime / 1000
    echo=False             # True для отладки SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Генератор для FastAPI/обычного использования"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
