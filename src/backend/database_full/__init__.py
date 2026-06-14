"""
CareForMe - Виртуальный сад с системой уровней и достижений.

Пакет для работы с базой данных виртуального сада.
Содержит репозитории, сервисы и API интерфейсы.

Основные возможности:
    - Система авторизации пользователей
    - Выращивание растений (Спатифиллум, Кактус, Фикус)
    - Система уровней с заданиями (1-5 уровни)
    - Достижения (ачивки) - эмоциональная ценность
    - Дизайны горшков и леек (открываются за задания)
"""

from .database.db_manager import get_db_manager, DatabaseManager
from .database.raw_sql_loader import (
    load_plants_from_csv_raw,
    load_achievements_from_csv_raw,
    verify_data,
)


from .auth.auth_manager import auth_manager
from .service.flower_service import FlowerService, flower_service
from .service.challenge_service import ChallengeService, challenge_service
from .service.user_service import UserService, user_service
from .service.level_quest_service import LevelQuestService, level_quest_service
from .repository.base_repository import BaseRepository
from .repository.user_repository import UserRepository
from .repository.plant_repository import PlantRepository
from .repository.challenge_repository import ChallengeRepository
from .repository.mistake_repository import MistakeRepository
from .repository.level_quest_repository import LevelQuestRepository, level_quest_repo
from .interface.flower_interface import FlowerInterface
from .interface.challenge_interface import ChallengeInterface
from .interface.user_interface import UserInterface, user_interface
from .interface.level_quest_interface import LevelQuestInterface, level_quest_interface
from .interface.user_interface import register, login, logout
__all__ = [
    # Database
    'get_db_manager',
    'DatabaseManager',
    'load_plants_from_csv_raw',
    'load_achievements_from_csv_raw',
    'verify_data',

    # Auth
    'auth_manager',

    # Services
    'FlowerService',
    'flower_service',
    'ChallengeService',
    'challenge_service',
    'UserService',
    'user_service',
    'LevelQuestService',
    'level_quest_service',

    # Repositories
    'BaseRepository',
    'UserRepository',
    'PlantRepository',
    'ChallengeRepository',
    'MistakeRepository',
    'LevelQuestRepository',
    'level_quest_repo',

    # Interfaces
    'FlowerInterface',
    'ChallengeInterface',
    'UserInterface',
    'user_interface',
    'LevelQuestInterface',
    'level_quest_interface',

    # Quick functions
    'register',
    'login',
    'logout',
    'get_current_user'
]