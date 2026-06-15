"""
CareForMe — Виртуальный сад с системой уровней и достижений.

Пакет для работы с базой данных виртуального сада.
"""

from .database.db_manager import get_db_manager, DatabaseManager
from .database.raw_sql_loader import (
    load_plants_from_csv_raw,
    load_achievements_from_csv_raw,
    load_tips_from_csv_raw,
    load_level_requirements_from_csv_raw,
    verify_data,
)

from .auth.auth_manager import auth_manager

from .service.user_service        import UserService,       user_service
from .service.flower_service      import FlowerService,     flower_service
from .service.challenge_service   import ChallengeService,  challenge_service
from .service.level_quest_service import LevelQuestService, level_quest_service

# Репозитории
from .repository.user_repository         import UserRepository
from .repository.plant_repository        import PlantRepository
from .repository.challenge_repository    import ChallengeRepository
from .repository.mistake_repository      import MistakeRepository
from .repository.level_quest_repository  import LevelQuestRepository, level_quest_repo
from .repository.base_repository         import BaseRepository

# Интерфейсы — только те, что не создают цикл через room_game_service
# game_interface импортируется напрямую в web/game_state.py
from .interface.flower_interface      import flower_interface
from .interface.challenge_interface   import challenge_interface
from .interface.level_quest_interface import level_quest_interface
from .interface.tips_interface        import tips_interface
from .interface.user_interface        import user_interface

__all__ = [
    # Database
    'get_db_manager',
    'DatabaseManager',
    'load_plants_from_csv_raw',
    'load_achievements_from_csv_raw',
    'load_tips_from_csv_raw',
    'load_level_requirements_from_csv_raw',
    'verify_data',

    # Auth
    'auth_manager',

    # Services
    'UserService',       'user_service',
    'FlowerService',     'flower_service',
    'ChallengeService',  'challenge_service',
    'LevelQuestService', 'level_quest_service',

    # Repositories
    'BaseRepository',
    'UserRepository',
    'PlantRepository',
    'ChallengeRepository',
    'MistakeRepository',
    'LevelQuestRepository', 'level_quest_repo',

    # Interfaces
    'flower_interface',
    'challenge_interface',
    'level_quest_interface',
    'tips_interface',
    'user_interface',
]