"""Интерфейс для работы с достижениями.

Предоставляет внешний API для работы с достижениями и наградами.
"""

from typing import List, Dict, Any
from ..service.challenge_service import ChallengeService


class ChallengeInterface:
    """Интерфейс для API - вызывает методы ChallengeService.

    Attributes:
        _service (ChallengeService): Сервисный слой для бизнес-логики
    """

    def __init__(self, db_path: str = None):
        """Инициализирует интерфейс с сервисным слоем.

        :param db_path: Путь к БД (опционально)
        :type db_path: str, optional
        """
        self._service = ChallengeService()

    def get_all_achievements(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Получить все достижения.

        :param user_id: ID пользователя (если указан, возвращает прогресс)
        :type user_id: str, optional
        :return: Список достижений
        :rtype: List[Dict[str, Any]]
        """
        return self._service.get_achievements(user_id) if user_id else self._service.get_achievements(None)

    def get_completed(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить выполненные достижения пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Список выполненных достижений
        :rtype: List[Dict[str, Any]]
        """
        return self._service.get_completed(user_id)

    def get_pending_rewards(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить незабранные награды пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Список достижений с незабранными наградами
        :rtype: List[Dict[str, Any]]
        """
        return self._service.get_unclaimed(user_id)

    def check_all_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Проверить все достижения пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Список вновь выполненных достижений
        :rtype: List[Dict[str, Any]]
        """
        return self._service.check_all(user_id)

    def claim_achievement_reward(self, user_id: str, achievement_id: str) -> Dict[str, Any]:
        """Забрать награду за достижение.

        :param user_id: ID пользователя
        :type user_id: str
        :param achievement_id: ID достижения
        :type achievement_id: str
        :return: Результат получения награды
        :rtype: Dict[str, Any]

        :example:
            >>> interface = ChallengeInterface()
            >>> result = interface.claim_achievement_reward("user123", "ach_001")
            >>> if result['success']:
            ...     print(result['message'])
            Награда получена! +50 монет
        """
        return self._service.claim_reward(user_id, achievement_id)

    def record_mistake(self, user_id: str, plant_id: str, mistake_type: str) -> Dict[str, Any]:
        """Записать ошибку пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param plant_id: ID растения
        :type plant_id: str
        :param mistake_type: Тип ошибки (overwater, drought, light, cold)
        :type mistake_type: str
        :return: Результат с новыми достижениями
        :rtype: Dict[str, Any]

        :example:
            >>> interface = ChallengeInterface()
            >>> result = interface.record_mistake("user123", "plant456", "overwater")
            >>> print(result['new_achievements'])
        """
        return self._service.record_mistake(user_id, plant_id, mistake_type)

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Получить статистику пользователя по достижениям.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Словарь со статистикой
        :rtype: Dict[str, Any]

        :returns::
            {
                "plants_grown_to_maturity": 3,
                "death_count": 1,
                "mistake_count": 5,
                "species_collected": 4,
                "consecutive_days": 7,
                "level": 3,
                "total_achievements": 2
            }
        """
        return self._service.get_statistics(user_id)