"""Интерфейс для работы с достижениями"""
from typing import List, Dict, Any
from ..service.challenge_service import ChallengeService


class ChallengeInterface:
    """Интерфейс для API - вызывает методы ChallengeService"""

    def __init__(self, db_path: str = None):
        self._service = ChallengeService()

    def get_all_achievements(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Получить все достижения"""
        return self._service.get_achievements(user_id) if user_id else self._service.get_achievements(None)

    def get_completed(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить выполненные достижения"""
        return self._service.get_completed(user_id)

    def get_pending_rewards(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить незабранные награды"""
        return self._service.get_unclaimed(user_id)

    def check_all_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Проверить все достижения"""
        return self._service.check_all(user_id)

    def claim_achievement_reward(self, user_id: str, achievement_id: str) -> Dict[str, Any]:
        """Забрать награду"""
        return self._service.claim_reward(user_id, achievement_id)

    def record_mistake(self, user_id: str, plant_id: str, mistake_type: str) -> Dict[str, Any]:
        """Записать ошибку"""
        return self._service.record_mistake(user_id, plant_id, mistake_type)

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Получить статистику"""
        return self._service.get_statistics(user_id)