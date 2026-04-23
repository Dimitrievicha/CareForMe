"""Сервис пользователя - профиль, опыт, монеты, серии"""
from typing import Optional, Dict, Any, List
from datetime import date

from ..repository.user_repository import UserRepository


class UserService:
    def __init__(self):
        self.user_repo = UserRepository()

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.user_repo.get_profile(user_id)

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"level": 0, "xp": 0, "coins": 0}

        return {
            "level": profile['level'],
            "xp": profile['xp'],
            "coins": profile['coins'],
            "total_plants_grown": profile['total_plants_grown'],
            "total_waterings": profile['total_waterings'],
            "current_plants": profile['current_plants_count'],
            "max_plants_slots": profile['max_plants_slots']
        }

    def add_xp(self, user_id: str, amount: int) -> Dict[str, Any]:
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"success": False}

        new_xp = profile['xp'] + amount
        current_level = profile['level']

        # Проверка повышения уровня
        next_level = self.user_repo.execute_query(
            "SELECT * FROM level_requirements WHERE level = ?",
            (current_level + 1,)
        )

        leveled_up = False
        if next_level and new_xp >= next_level[0]['required_xp']:
            leveled_up = True
            new_level = current_level + 1

            if next_level[0]['reward_coins'] > 0:
                self.user_repo.add_coins(user_id, next_level[0]['reward_coins'])

            if next_level[0]['reward_new_plant_slot']:
                self.user_repo.update_plant_slots(user_id, 1)
        else:
            new_level = current_level

        self.user_repo.update_xp(user_id, new_xp, new_level)

        return {
            "success": True,
            "old_level": current_level,
            "new_level": new_level,
            "xp_gained": amount,
            "leveled_up": leveled_up
        }

    def add_coins(self, user_id: str, amount: int) -> bool:
        return self.user_repo.add_coins(user_id, amount)

    def update_daily_streak(self, user_id: str) -> Dict[str, Any]:
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"success": False}

        today = date.today()
        last_entry = date.fromisoformat(profile['last_entry']) if profile['last_entry'] else None

        if last_entry == today:
            return {"updated": False, "consecutive_days": profile['consecutive_days']}

        if last_entry and (today - last_entry).days == 1:
            new_streak = profile['consecutive_days'] + 1
        else:
            new_streak = 1

        best_streak = max(profile['best_streak'], new_streak)
        self.user_repo.update_streak(user_id, new_streak, best_streak)

        return {
            "success": True,
            "consecutive_days": new_streak,
            "best_streak": best_streak
        }

    def get_plant_slots(self, user_id: str) -> Dict[str, int]:
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"current": 0, "max": 1, "available": 1}

        return {
            "current": profile['current_plants_count'],
            "max": profile['max_plants_slots'],
            "available": profile['max_plants_slots'] - profile['current_plants_count']
        }

    def increment_current_plants(self, user_id: str, delta: int = 1) -> bool:
        return self.user_repo.update_current_plants_count(user_id, delta)


user_service = UserService()