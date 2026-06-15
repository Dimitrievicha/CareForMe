"""
Пакет интерфейсов.
Предоставляет глобальные экземпляры для вызова из Blueprint'ов.
"""

from .challenge_interface   import ChallengeInterface,  challenge_interface
from .flower_interface      import FlowerInterface,      flower_interface
from .level_quest_interface import LevelQuestInterface,  level_quest_interface
from .tips_interface        import TipsInterface,        tips_interface
from .user_interface        import UserInterface,        user_interface


__all__ = [
    'ChallengeInterface',  'challenge_interface',
    'FlowerInterface',     'flower_interface',
    'LevelQuestInterface', 'level_quest_interface',
    'TipsInterface',       'tips_interface',
    'UserInterface',       'user_interface',
]