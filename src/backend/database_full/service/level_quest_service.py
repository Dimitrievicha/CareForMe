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
from ..repository.game_repository import GameRepository
from ..database.db_manager import get_db_manager
from .user_service import user_service


class LevelQuestService:
    """
    Сервис для управления уровневыми заданиями.
    """

    def __init__(self):
        """Инициализирует сервис с необходимыми репозиториями."""
        self.user_repo = UserRepository()
        self.plant_repo = PlantRepository()
        self.challenge_repo = ChallengeRepository()
        self.mistake_repo = MistakeRepository()
        self.game_repo = GameRepository()
        self.db = get_db_manager()

    def _game_flags(self, user_id: str) -> dict:
        state = self.game_repo.load_game_state(user_id) or {}
        return state.get('achievements') or {}

    def get_level_quests(self, level: int) -> Optional[Dict[str, Any]]:
        """Получает задания для указанного уровня."""
        result = self.db.execute_query(
            "SELECT * FROM level_requirements WHERE level = ?",
            (level,)
        )
        return result[0] if result else None

    def get_user_level_progress(self, user_id: str, level: int) -> Optional[Dict[str, Any]]:
        """Получает прогресс пользователя по заданиям уровня."""
        result = self.db.execute_query("""
            SELECT * FROM user_level_progress 
            WHERE user_id = ? AND level = ?
        """, (user_id, level))
        return result[0] if result else None

    def init_user_level_progress(self, user_id: str, level: int) -> bool:
        """Инициализирует прогресс для нового уровня."""
        return self.db.execute_update("""
            INSERT INTO user_level_progress (user_id, level, quest1_progress, quest2_progress, quest3_progress)
            VALUES (?, ?, 0, 0, 0)
        """, (user_id, level))

    def _check_quest_completion(self, user_id: str, quest_type: str, target: int) -> int:
        """
        Проверяет прогресс выполнения конкретного задания.

        Returns:
            Текущий прогресс (всегда int)
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return 0

        # Посадка первого растения
        if quest_type == 'plant_first':
            return 1 if profile['total_plants_grown'] >= 1 else 0

        # Количество поливов (water_count, water_once, water_3times, water_6times)
        elif quest_type in ('water_count', 'water_once', 'water_3times', 'water_6times'):
            return profile['total_waterings']

        # Прочтение совета/описания
        elif quest_type == 'read_tip':
            flags = self._game_flags(user_id)
            return 1 if flags.get('__readDescriptionDone') else 0

        # Выращивание до стадии 2 (grow_to_stage_2, grow_stage2)
        elif quest_type in ('grow_to_stage_2', 'grow_stage2'):
            plants = self.plant_repo.get_plants_by_stage(user_id, 'seedling') or []
            plants += self.plant_repo.get_plants_by_stage(user_id, 'growing') or []
            plants += self.plant_repo.get_plants_by_stage(user_id, 'mature') or []
            plants += self.plant_repo.get_plants_by_stage(user_id, 'flowering') or []
            return len(plants)

        # Ежедневный вход (daily_login_streak, login_3days, login_5days, login_7days, login_10days)
        elif quest_type in ('daily_login_streak', 'login_3days', 'login_5days', 'login_7days', 'login_10days'):
            return profile['consecutive_days']

        # Лечение растения
        elif quest_type == 'heal_plant':
            flags = self._game_flags(user_id)
            return 1 if flags.get('__healedPlant') else 0

        # Выращивание разных видов (grow_different_species, grow_2species)
        elif quest_type in ('grow_different_species', 'grow_2species'):
            return self.challenge_repo.check_species_collected(user_id)

        # Без ошибок X дней
        elif quest_type in ('no_mistakes_streak', 'no_mistakes_7days'):
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

        # Выращивание всех видов (grow_all_species, grow_3rd_plant)
        elif quest_type in ('grow_all_species', 'grow_3rd_plant'):
            return self.challenge_repo.check_species_collected(user_id)

        # Количество полученных достижений
        elif quest_type == 'get_achievements_count':
            return len(self.challenge_repo.get_completed_achievements(user_id))

        return 0

    def check_and_update_quests(self, user_id: str) -> Dict[str, Any]:
        """
        Проверяет все задания для текущего уровня пользователя.
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"success": False, "error": "Пользователь не найден"}

        current_level = profile['current_level']

        if current_level >= 6:  # Максимальный уровень 6
            return {"success": True, "max_level_reached": True, "leveled_up": False}

        quests = self.get_level_quests(current_level)
        if not quests:
            return {"success": False, "error": f"Задания для уровня {current_level} не найдены"}

        progress = self.get_user_level_progress(user_id, current_level)
        if not progress:
            self.init_user_level_progress(user_id, current_level)
            progress = self.get_user_level_progress(user_id, current_level)

        quests_completed = []

        # Проверка задания 1
        if not progress['quest1_completed'] and quests.get('quest1_type'):
            q1_progress = self._check_quest_completion(user_id, quests['quest1_type'], quests['quest1_target'])
            self.db.execute_update("""
                UPDATE user_level_progress SET quest1_progress = ?
                WHERE user_id = ? AND level = ?
            """, (q1_progress, user_id, current_level))

            if q1_progress >= quests['quest1_target']:
                self.db.execute_update("""
                    UPDATE user_level_progress SET quest1_completed = 1
                    WHERE user_id = ? AND level = ?
                """, (user_id, current_level))
                quests_completed.append(1)

        # Проверка задания 2
        if quests.get('quest2_type') and not progress['quest2_completed']:
            q2_progress = self._check_quest_completion(user_id, quests['quest2_type'], quests['quest2_target'])
            self.db.execute_update("""
                UPDATE user_level_progress SET quest2_progress = ?
                WHERE user_id = ? AND level = ?
            """, (q2_progress, user_id, current_level))

            if q2_progress >= quests['quest2_target']:
                self.db.execute_update("""
                    UPDATE user_level_progress SET quest2_completed = 1
                    WHERE user_id = ? AND level = ?
                """, (user_id, current_level))
                quests_completed.append(2)

        # Проверка задания 3
        if quests.get('quest3_type') and not progress['quest3_completed']:
            q3_progress = self._check_quest_completion(user_id, quests['quest3_type'], quests['quest3_target'])
            self.db.execute_update("""
                UPDATE user_level_progress SET quest3_progress = ?
                WHERE user_id = ? AND level = ?
            """, (q3_progress, user_id, current_level))

            if q3_progress >= quests['quest3_target']:
                self.db.execute_update("""
                    UPDATE user_level_progress SET quest3_completed = 1
                    WHERE user_id = ? AND level = ?
                """, (user_id, current_level))
                quests_completed.append(3)

        # Обновляем прогресс после всех проверок
        progress = self.get_user_level_progress(user_id, current_level)

        # Проверяем, все ли задания выполнены
        all_completed = True
        if quests.get('quest1_type') and not progress['quest1_completed']:
            all_completed = False
        if quests.get('quest2_type') and not progress['quest2_completed']:
            all_completed = False
        if quests.get('quest3_type') and not progress['quest3_completed']:
            all_completed = False

        if all_completed and not progress['level_completed']:
            # Отмечаем уровень как завершённый
            self.db.execute_update("""
                UPDATE user_level_progress 
                SET level_completed = 1, completed_at = CURRENT_DATE
                WHERE user_id = ? AND level = ?
            """, (user_id, current_level))

            # Повышаем уровень
            new_level = current_level + 1
            self.user_repo.update_level(user_id, new_level)

            # Выдаём награду
            reward = self._claim_reward(user_id, current_level, quests)

            # Инициализируем прогресс для нового уровня
            if new_level <= 6:
                self.init_user_level_progress(user_id, new_level)

            return {
                "success": True,
                "leveled_up": True,
                "old_level": current_level,
                "new_level": new_level,
                "reward": reward,
                "quests_completed": len(quests_completed)
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
        """
        reward_type = quests['reward_type']
        reward_value = quests['reward_value']
        reward_description = quests['reward_description']

        result = {"type": reward_type, "value": reward_value, "description": reward_description}

        print(f"DEBUG: Выдача награды за уровень {level}: type={reward_type}, value={reward_value}")

        if reward_type == 'new_pot':
            # reward_value = '2' - ID горшка
            pot_id = reward_value
            user_service.unlock_pot(user_id, str(pot_id))
            print(f"DEBUG: Разблокирован горшок {pot_id} для пользователя {user_id}")

        elif reward_type == 'new_can' or reward_type == 'new_watering_can':
            # reward_value = '2' - ID лейки
            can_id = reward_value
            user_service.unlock_watering_can(user_id, str(can_id))
            print(f"DEBUG: Разблокирована лейка {can_id} для пользователя {user_id}")

        elif reward_type == 'new_plant_slot' or reward_type == 'new_slot':
            # reward_value может быть пустым
            user_service.add_plant_slot(user_id)
            print(f"DEBUG: Добавлен слот для растения пользователю {user_id}")

            # Также разблокируем новый вид растения, если указан
            if reward_value and reward_value.isdigit():
                # Это ID растения для разблокировки (1, 2, 3)
                pass

        elif reward_type == 'new_plant':
            print(f"DEBUG: Разблокировано новое растение с ID {reward_value}")

        elif reward_type == 'achievement':
            # reward_value = 'Страж флоры'
            achievement = self.challenge_repo.get_achievement_by_name(reward_value)
            if achievement:
                self.challenge_repo.update_progress(user_id, achievement['id'], 1)
                self.challenge_repo.complete_achievement(user_id, achievement['id'])
                print(f"DEBUG: Выдано достижение {reward_value}")

            # Также выдаём большой горшок за 5 уровень
            if level == 5:
                user_service.unlock_pot(user_id, '3')
                print(f"DEBUG: Разблокирован большой горшок 3")

        self.db.execute_update("""
            UPDATE user_level_progress SET reward_claimed = 1
            WHERE user_id = ? AND level = ?
        """, (user_id, level))

        return result

    def trigger_quest_check(self, user_id: str, action: str) -> Dict[str, Any]:
        """Триггер для проверки заданий после действия пользователя."""
        return self.check_and_update_quests(user_id)

    def get_all_quests_status(self, user_id: str) -> Dict[int, Dict[str, Any]]:
        """Получает статус всех заданий для всех уровней."""
        result = {}
        profile = self.user_repo.get_profile(user_id)
        current_level = profile['current_level'] if profile else 1

        for level in range(1, 7):
            quests = self.get_level_quests(level)
            progress = self.get_user_level_progress(user_id, level)

            if level < current_level:
                status = "completed"
            elif level == current_level:
                status = "in_progress"
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