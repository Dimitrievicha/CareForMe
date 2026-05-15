"""
API маршруты Flask приложения
Экспортирует все Blueprint'ы для регистрации в app.py
"""

from .auth import auth_bp
from .garden import garden_bp
from .quests import quests_bp
from .achievements import achievements_bp
from .user import user_bp
from .plants import plants_bp
from .tips import tips_bp

__all__ = [
    'auth_bp',
    'garden_bp',
    'quests_bp',
    'achievements_bp',
    'user_bp',
    'plants_bp',
    'tips_bp'
]