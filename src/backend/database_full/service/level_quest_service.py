"""
Сервис для управления уровневыми заданиями.

Обрабатывает прогресс заданий и выдачу наград за повышение уровня.
Уровень повышается ТОЛЬКО при выполнении всех заданий текущего уровня.

"""

from typing import Dict, Any, Optional, List
from datetime import date

from ..repository.user_repository import UserRepository
from ..repository.plant_repository import PlantRepository
from ..repository.challenge_repository import ChallengeRepository
from ..repository.mistake_repository import MistakeRepository
from ..database.db_manager import get_db_manager
from .user_service import user_service


class LevelQuestService:
    """
    Сервис для управления уровневыми заданиями.

    Отслеживает прогресс выполнения заданий для каждого уровня.
    При выполнении всех заданий повышает уровень и выдает награду.

    Attributes:
        user_repo (UserRepository): Репозиторий пользователей
        plant_repo (PlantRepository): Репозиторий растений
        challenge_repo (ChallengeRepository): Репозиторий достижений
        mistake_repo (MistakeRepository): Репозиторий ошибок
        db (DatabaseManager): Менеджер БД
    """

    def __init__(self):
        """Инициализирует сервис TESTING_REPORT.md необходимыми репозиториями."""
        self.user_repo = UserRepository()
        self.plant_repo = PlantRepository()
        self.challenge_repo = ChallengeRepository()
        self.mistake_repo = MistakeRepository()
        self.db = get_db_manager()

    def get_level_quests(self, level: int) -> Optional[Dict[str, Any]]:
        """
        Получает задания для указанного уровня.

        Args:
            level: Номер уровня (1-5)

        Returns:
            Данные заданий уровня

        Returns структура:
            {
                "level": 1,
                "quest1_type": "plant_first",
                "quest1_target": 1,
                "quest1_description": "Посадить первое растение",
                "quest2_type": "water_count",
                "quest2_target": 1,
                "quest2_description": "Полить растение 1 раз",
                "quest3_type": "read_tip",
                "quest3_target": 1,
                "quest3_description": "Прочитать 1 совет",
                "reward_type": "new_pot",
                "reward_value": "design_pot_1",
                "reward_description": "1 новый дизайнерский горшок"
            }
        """
        result = self.db.execute_query(
            "SELECT * FROM level_requirements WHERE level = ?",
            (level,)
        )
        return result[0] if result else None

    def get_user_level_progress(self, user_id: str, level: int) -> Optional[Dict[str, Any]]:
        """
        Получает прогресс пользователя по заданиям уровня.

        Args:
            user_id: ID пользователя
            level: Номер уровня

        Returns:
            Прогресс заданий или None если еще не инициализирован
        """
        result = self.db.execute_query("""
            SELECT * FROM user_level_progress 
            WHERE user_id = ? AND level = ?
        """, (user_id, level))
        return result[0] if result else None

    def init_user_level_progress(self, user_id: str, level: int) -> bool:
        """
        Инициализирует прогресс для нового уровня.

        Args:
            user_id: ID пользователя
            level: Номер уровня

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            INSERT INTO user_level_progress (user_id, level, quest1_progress, quest2_progress, quest3_progress)
            VALUES (?, ?, 0, 0, 0)
        """, (user_id, level))

    def _check_quest_completion(self, user_id: str, quest_type: str, target: int) -> int:
        """
        Проверяет прогресс выполнения конкретного задания.

        Args:
            user_id: ID пользователя
            quest_type: Тип задания
            target: Целевое значение

        Returns:
            Текущий прогресс (число)
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return 0

        if quest_type == 'plant_first':
            return 1 if profile['total_plants_grown'] >= 1 else 0

        elif quest_type == 'water_count':
            return profile['total_waterings']

        elif quest_type == 'read_tip':
            return self.mistake_repo.get_mistakes_count(user_id)

        elif quest_type == 'grow_to_stage_2':
            plants = self.plant_repo.get_plants_by_stage(user_id, 'seedling')
            plants += self.plant_repo.get_plants_by_stage(user_id, 'growing')
            plants += self.plant_repo.get_plants_by_stage(user_id, 'mature')
            plants += self.plant_repo.get_plants_by_stage(user_id, 'flowering')
            return len(plants)

        elif quest_type == 'daily_login_streak':
            return profile['consecutive_days']

        elif quest_type == 'heal_plant':
            return self.mistake_repo.get_mistakes_count(user_id) // 2

        elif quest_type == 'grow_different_species':
            return self.challenge_repo.check_species_collected(user_id)

        elif quest_type == 'no_mistakes_streak':
            today_mistakes = self.mistake_repo.get_today_mistakes(user_id)
            if today_mistakes > 0:
                return 0
            mistakes = self.mistake_repo.get_user_mistakes(user_id, limit=1)
            if not mistakes:
                return profile['consecutive_days']
            from datetime import datetime
            last_mistake = datetime.fromisoformat(mistakes[0]['occurred_at']).date()
            days_since = (date.today() - last_mistake).days
            return days_since

        elif quest_type == 'grow_all_species':
            return self.challenge_repo.check_species_collected(user_id)

        elif quest_type == 'get_achievements_count':
            return len(self.challenge_repo.get_completed_achievements(user_id))

        return 0

    def check_and_update_quests(self, user_id: str) -> Dict[str, Any]:
        """
        Проверяет все задания для текущего уровня пользователя.

        Вызывается после каждого действия (полив, посадка, ошибка и т.д.).

        Args:
            user_id: ID пользователя

        Returns:
            Результат проверки TESTING_REPORT.md информацией о повышении уровня

        Returns структура:
            {
                "success": True,
                "leveled_up": True,
                "old_level": 1,
                "new_level": 2,
                "reward": {
                    "type": "new_pot",
                    "value": "design_pot_1",
                    "description": "1 новый дизайнерский горшок"
                }
            }
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"success": False, "error": "Пользователь не найден"}

        current_level = profile['current_level']

        if current_level >= 5:
            return {"success": True, "max_level_reached": True, "leveled_up": False}

        quests = self.get_level_quests(current_level)
        if not quests:
            return {"success": False, "error": f"Задания для уровня {current_level} не найдены"}

        progress = self.get_user_level_progress(user_id, current_level)
        if not progress:
            self.init_user_level_progress(user_id, current_level)
            progress = self.get_user_level_progress(user_id, current_level)

        quests_completed = []

        if not progress['quest1_completed']:
            q1_progress = self._check_quest_completion(user_id, quests['quest1_type'], quests['quest1_target'])
            if q1_progress >= quests['quest1_target']:
                self.db.execute_update("""
                    UPDATE user_level_progress 
                    SET quest1_completed = 1, quest1_progress = ?
                    WHERE user_id = ? AND level = ?
                """, (q1_progress, user_id, current_level))
                quests_completed.append(1)
            else:
                self.db.execute_update("""
                    UPDATE user_level_progress SET quest1_progress = ?
                    WHERE user_id = ? AND level = ?
                """, (q1_progress, user_id, current_level))

        if quests['quest2_type'] and not progress['quest2_completed']:
            q2_progress = self._check_quest_completion(user_id, quests['quest2_type'], quests['quest2_target'])
            if q2_progress >= quests['quest2_target']:
                self.db.execute_update("""
                    UPDATE user_level_progress 
                    SET quest2_completed = 1, quest2_progress = ?
                    WHERE user_id = ? AND level = ?
                """, (q2_progress, user_id, current_level))
                quests_completed.append(2)
            else:
                self.db.execute_update("""
                    UPDATE user_level_progress SET quest2_progress = ?
                    WHERE user_id = ? AND level = ?
                """, (q2_progress, user_id, current_level))

        if quests['quest3_type'] and not progress['quest3_completed']:
            q3_progress = self._check_quest_completion(user_id, quests['quest3_type'], quests['quest3_target'])
            if q3_progress >= quests['quest3_target']:
                self.db.execute_update("""
                    UPDATE user_level_progress 
                    SET quest3_completed = 1, quest3_progress = ?
                    WHERE user_id = ? AND level = ?
                """, (q3_progress, user_id, current_level))
                quests_completed.append(3)
            else:
                self.db.execute_update("""
                    UPDATE user_level_progress SET quest3_progress = ?
                    WHERE user_id = ? AND level = ?
                """, (q3_progress, user_id, current_level))

        all_completed = (
                                progress['quest1_completed'] or 1 in quests_completed
                        ) and (
                                not quests['quest2_type'] or (progress['quest2_completed'] or 2 in quests_completed)
                        ) and (
                                not quests['quest3_type'] or (progress['quest3_completed'] or 3 in quests_completed)
                        )

        if all_completed and not progress['level_completed']:
            self.db.execute_update("""
                UPDATE user_level_progress 
                SET level_completed = 1, completed_at = CURRENT_DATE
                WHERE user_id = ? AND level = ?
            """, (user_id, current_level))

            new_level = current_level + 1
            self.user_repo.update_level(user_id, new_level)

            reward = self._claim_reward(user_id, current_level, quests)

            if new_level <= 5:
                self.init_user_level_progress(user_id, new_level)

            return {
                "success": True,
                "leveled_up": True,
                "old_level": current_level,
                "new_level": new_level,
                "reward": reward
            }

        return {
            "success": True,
            "leveled_up": False,
            "current_level": current_level,
            "quests_completed": len(quests_completed)
        }

    def _claim_reward(self, user_id: str, level: int, quests: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Выдает награду за завершение уровня.

        Args:
            user_id: ID пользователя
            level: Завершенный уровень
            quests: Данные заданий уровня

        Returns:
            Информация о выданной награде или None
        """
        reward_type = quests['reward_type']
        reward_value = quests['reward_value']
        reward_description = quests['reward_description']

        result = {"type": reward_type, "value": reward_value, "description": reward_description}

        if reward_type == 'new_pot':
            user_service.unlock_pot(user_id, reward_value)

        elif reward_type == 'new_watering_can':
            user_service.unlock_watering_can(user_id, reward_value)

        elif reward_type == 'new_plant_slot':
            user_service.add_plant_slot(user_id)

        elif reward_type == 'achievement':
            achievement = self.challenge_repo.get_achievement_by_name(reward_value)
            if achievement:
                self.challenge_repo.update_progress(user_id, achievement['id'], 1)
                self.challenge_repo.complete_achievement(user_id, achievement['id'])

        self.db.execute_update("""
            UPDATE user_level_progress SET reward_claimed = 1
            WHERE user_id = ? AND level = ?
        """, (user_id, level))

        return result

    def trigger_quest_check(self, user_id: str, action: str) -> Dict[str, Any]:
        """
        Триггер для проверки заданий после действия пользователя.

        Args:
            user_id: ID пользователя
            action: Тип действия (water, plant, mistake, read_tip и т.д.)

        Returns:
            Результат проверки заданий
        """
        return self.check_and_update_quests(user_id)

    def get_all_quests_status(self, user_id: str) -> Dict[int, Dict[str, Any]]:
        """
        Получает статус всех заданий для всех уровней.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь {уровень: статус}
        """
        result = {}
        profile = self.user_repo.get_profile(user_id)
        current_level = profile['current_level'] if profile else 1

        for level in range(1, 6):
            quests = self.get_level_quests(level)
            progress = self.get_user_level_progress(user_id, level)

            if level <= current_level:
                status = "completed" if (progress and progress['level_completed']) else "in_progress"
            elif level == current_level + 1:
                status = "locked_next"
            else:
                status = "locked"

            result[level] = {
                "status": status,
                "quests": quests,
                "progress": progress
            }

        return result


# Глобальный экземпляр
level_quest_service = LevelQuestService()