"""Сервис достижений - проверка, награды, ошибки"""
from typing import List, Dict, Any

from ..repository.challenge_repository import ChallengeRepository
from ..repository.mistake_repository import MistakeRepository
from ..repository.user_repository import UserRepository


class ChallengeService:
    def __init__(self):
        self.challenge_repo = ChallengeRepository()
        self.mistake_repo = MistakeRepository()
        self.user_repo = UserRepository()

    def get_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        return self.challenge_repo.get_user_achievements(user_id)

    def get_completed(self, user_id: str) -> List[Dict[str, Any]]:
        return self.challenge_repo.get_completed_achievements(user_id)

    def get_unclaimed(self, user_id: str) -> List[Dict[str, Any]]:
        return self.challenge_repo.get_unclaimed_rewards(user_id)

    def _get_progress(self, user_id: str, req_type: str) -> int:
        if req_type == 'grow_to_maturity':
            return self.challenge_repo.check_grow_to_maturity(user_id)
        elif req_type == 'death_first':
            return self.challenge_repo.check_death_first(user_id)
        elif req_type == 'mistake':
            return self.mistake_repo.get_mistakes_count(user_id)
        elif req_type == 'collect_species':
            return self.challenge_repo.check_species_collected(user_id)
        elif req_type == 'care_days':
            return self.challenge_repo.get_consecutive_days(user_id)
        elif req_type == 'level':
            return self.challenge_repo.get_level(user_id)
        return 0

    def check_all(self, user_id: str) -> List[Dict[str, Any]]:
        completed = []
        achievements = self.challenge_repo.get_all_achievements()

        for ach in achievements:
            progress = self._get_progress(user_id, ach['requirement_type'])
            self.challenge_repo.update_progress(user_id, ach['id'], progress)

            if progress >= ach['target_value']:
                if not self.challenge_repo.is_achievement_completed(user_id, ach['id']):
                    self.challenge_repo.complete_achievement(user_id, ach['id'])
                    completed.append(ach)

        return completed

    def claim_reward(self, user_id: str, achievement_id: str) -> Dict[str, Any]:
        achievements = self.challenge_repo.get_user_achievements(user_id)
        target = None

        for ach in achievements:
            if ach['id'] == achievement_id:
                target = ach
                break

        if not target:
            return {"success": False, "error": "Достижение не найдено"}
        if not target['is_completed']:
            return {"success": False, "error": "Достижение не выполнено"}
        if target['claimed']:
            return {"success": False, "error": "Награда уже получена"}

        if target['reward_coins'] > 0:
            self.user_repo.add_coins(user_id, target['reward_coins'])

        self.challenge_repo.claim_reward(user_id, achievement_id)

        return {"success": True, "message": f"Награда получена! +{target['reward_coins']} монет"}

    def record_mistake(self, user_id: str, plant_id: str, mistake_type: str) -> Dict[str, Any]:
        self.mistake_repo.add_mistake(user_id, plant_id, mistake_type)
        self.user_repo.increment_stat(user_id, "total_mistakes")
        completed = self.check_all(user_id)
        return {"success": True, "mistake_type": mistake_type, "new_achievements": completed}

    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """Получить полную статистику пользователя по достижениям"""

        return {
            "plants_grown_to_maturity": self.challenge_repo.check_grow_to_maturity(user_id),
            "death_count": self.challenge_repo.check_death_first(user_id),
            "mistake_count": self.mistake_repo.get_mistakes_count(user_id),
            "species_collected": self.challenge_repo.check_species_collected(user_id),
            "consecutive_days": self.challenge_repo.get_consecutive_days(user_id),
            "level": self.challenge_repo.get_level(user_id),
            "total_achievements": len(self.challenge_repo.get_completed_achievements(user_id))
        }


challenge_service = ChallengeService()