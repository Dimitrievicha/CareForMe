"""CareForMe Database Package

Пакет для работы с базой данных виртуального сада.
Содержит репозитории, сервисы и API интерфейсы.
"""

# Database core
from .database.db_manager import get_db_manager, DatabaseManager
from .database.raw_sql_loader import (
    load_plants_from_csv_raw,
    load_achievements_from_csv_raw,
    verify_data
)

# Auth
from .auth.auth_manager import AuthManager, auth_manager

# Services
from .service.flower_service import FlowerService
from .service.challenge_service import ChallengeService
from .service.user_service import UserService

# Repositories (добавить это!)
from .repository.base_repository import BaseRepository
from .repository.user_repository import UserRepository
from .repository.plant_repository import PlantRepository
from .repository.challenge_repository import ChallengeRepository
from .repository.mistake_repository import MistakeRepository

# Interfaces
from .interface.flower_interface import FlowerInterface
from .interface.challenge_interface import ChallengeInterface
from .interface.user_interface import UserInterface, user_interface

__all__ = [
    # Database
    'get_db_manager',
    'DatabaseManager',
    'load_plants_from_csv_raw',
    'load_achievements_from_csv_raw',
    'verify_data',

    # Auth
    'AuthManager',
    'auth_manager',

    # Services
    'FlowerService',
    'ChallengeService',
    'UserService',

    # Repositories
    'BaseRepository',
    'UserRepository',
    'PlantRepository',
    'ChallengeRepository',
    'MistakeRepository',

    # Interfaces
    'FlowerInterface',
    'ChallengeInterface',
    'UserInterface',
    'user_interface'
]