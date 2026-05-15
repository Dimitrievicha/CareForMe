"""
Конфигурация Flask приложения
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Базовые настройки"""

    # Секретный ключ
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Режим отладки
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # База данных
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///careforme.db')

    # Настройки сессии
    # SESSION_TYPE = 'filesystem'  # требует flask-session, используем встроенные cookie-сессии Flask
    PERMANENT_SESSION_LIFETIME = 86400  # 24 часа

    # CORS
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5000', 'http://localhost']

    # JWT (для API)
    JWT_SECRET = os.environ.get('JWT_SECRET', SECRET_KEY)
    JWT_EXPIRES_HOURS = 24


class DevelopmentConfig(Config):
    """Настройки для разработки"""
    DEBUG = True
    DATABASE_URL = os.environ.get('DEV_DATABASE_URL', 'sqlite:///careforme_dev.db')


class ProductionConfig(Config):
    """Настройки для продакшена"""
    DEBUG = False
    DATABASE_URL = os.environ.get('DATABASE_URL')

    # Безопасность
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


# Выбор конфигурации
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])