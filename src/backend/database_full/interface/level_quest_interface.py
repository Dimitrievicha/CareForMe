"""
Интерфейс для работы с уровневыми заданиями.

Предоставляет внешний API для работы с системой уровней:
    - Просмотр заданий для уровней
    - Проверка прогресса
    - Получение наград

"""

from typing import Dict, Any, List, Optional
from ..service.level_quest_service import level_quest_service
from ..service.user_service import user_service
from ..repository.level_quest_repository import level_quest_repo


class LevelQuestInterface:
    """
    Интерфейс для API - вызывает методы LevelQuestService.

    Предоставляет упрощенный доступ к функционалу уровневых заданий:
        - Просмотр заданий для каждого уровня
        - Отслеживание прогресса
        - Принудительная проверка заданий

    Attributes:
        _service (LevelQuestService): Сервисный слой для бизнес-логики
    """

    def __init__(self):
        """Инициализирует интерфейс с сервисным слоем."""
        self._service = level_quest_service
        self._user_service = user_service

    def get_level_quests(self, level: int) -> Optional[Dict[str, Any]]:
        """
        Получить задания для указанного уровня.

        Args:
            level: Номер уровня (1-5)

        Returns:
            Данные заданий уровня или None

        """
        return level_quest_repo.get_level_quests(level)

    def get_all_levels_quests(self) -> List[Dict[str, Any]]:
        """
        Получить задания для всех уровней.

        Returns:
            Список заданий для уровней 1-5

        """
        return level_quest_repo.get_all_level_quests()

    def get_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Получить полную информацию о прогрессе пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Полная информация о прогрессе по уровням

        Returns структура:
            {
                "current_level": 2,
                "max_level": 5,
                "levels": {
                    1: {
                        "status": "completed",
                        "completed_at": "2024-01-01",
                        "reward_claimed": True
                    },
                    2: {
                        "status": "in_progress",
                        "quests": [...],
                        "reward_claimed": False
                    },
                    3: {"status": "locked"},
                    4: {"status": "locked"},
                    5: {"status": "locked"}
                }
            }

        """
        current_level = self._user_service.get_current_level(user_id)
        max_level = level_quest_repo.get_max_level()

        result = {
            "current_level": current_level,
            "max_level": max_level,
            "levels": {}
        }

        for level in range(1, max_level + 1):
            if level < current_level:
                progress = level_quest_repo.get_user_progress(user_id, level)
                result["levels"][level] = {
                    "status": "completed",
                    "completed_at": progress['completed_at'] if progress else None,
                    "reward_claimed": progress['reward_claimed'] if progress else False
                }
            elif level == current_level:
                level_progress = level_quest_repo.get_current_level_progress(user_id, current_level)
                result["levels"][level] = {
                    "status": "in_progress",
                    "quests": level_progress.get('quests', []),
                    "all_completed": level_progress.get('all_completed', False),
                    "reward_claimed": level_progress.get('reward_claimed', False)
                }
            else:
                quests_def = level_quest_repo.get_level_quests(level)
                result["levels"][level] = {
                    "status": "locked",
                    "required_level": level - 1,
                    "reward": {
                        "type": quests_def['reward_type'] if quests_def else None,
                        "description": quests_def['reward_description'] if quests_def else None
                    }
                }

        return result

    def get_current_level_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Получить прогресс по текущему уровню пользователя.
        """
        current_level = self._user_service.get_current_level(user_id)
        result = level_quest_repo.get_current_level_progress(user_id, current_level)

        if 'quests' in result:
            for quest in result['quests']:
                quest['completed'] = bool(quest.get('completed', False))

        return result

    def get_quest_progress(self, user_id: str, level: int, quest_number: int) -> Dict[str, Any]:
        """
        Получить прогресс конкретного задания.

        Args:
            user_id: ID пользователя
            level: Номер уровня
            quest_number: Номер задания (1, 2, 3)

        Returns:
            Прогресс задания

        Returns структура:
            {
                "quest_number": 1,
                "type": "plant_first",
                "progress": 1,
                "target": 1,
                "completed": True,
                "description": "Посадить первое растение"
            }
        """
        level_progress = level_quest_repo.get_current_level_progress(user_id, level)

        for quest in level_progress.get('quests', []):
            if quest['number'] == quest_number:
                return quest

        return {"error": f"Задание {quest_number} не найдено"}

    def check_quests(self, user_id: str) -> Dict[str, Any]:
        """
        Принудительно проверить выполнение заданий.

        Вызывается после каждого действия пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Результат проверки с информацией о повышении уровня

        Returns структура при повышении уровня:
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

        Returns структура без повышения:
            {
                "success": True,
                "leveled_up": False,
                "current_level": 2,
                "quests_completed": 1
            }

        """
        return self._service.check_and_update_quests(user_id)

    def trigger_check(self, user_id: str, action: str) -> Dict[str, Any]:
        """
        Триггер для проверки заданий после действия пользователя.

        Args:
            user_id: ID пользователя
            action: Тип действия (water, plant, mistake, read_tip, grow_to_mature, heal)

        Returns:
            Результат проверки заданий

        """
        return self._service.trigger_quest_check(user_id, action)

    def get_reward_info(self, level: int) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о награде за уровень.

        Args:
            level: Номер уровня

        Returns:
            Информация о награде

        """
        return level_quest_repo.get_reward_by_level(level)

    def get_next_reward(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о следующей награде.

        Args:
            user_id: ID пользователя

        Returns:
            Информация о награде за следующий уровень

        """
        current_level = self._user_service.get_current_level(user_id)
        if current_level >= 5:
            return None
        return self.get_reward_info(current_level + 1)

    def get_total_completed_levels(self, user_id: str) -> int:
        """
        Получить количество выполненных уровней.

        Args:
            user_id: ID пользователя

        Returns:
            Количество завершенных уровней (0-5)
        """
        progress_list = level_quest_repo.get_all_user_progress(user_id)
        completed = 0
        for p in progress_list:
            if p['level_completed']:
                completed += 1
        return completed

    def is_max_level_reached(self, user_id: str) -> bool:
        """
        Проверить, достиг ли пользователь максимального уровня.

        Args:
            user_id: ID пользователя

        Returns:
            True если уровень 5 достигнут
        """
        current_level = self._user_service.get_current_level(user_id)
        return current_level >= 5

    def get_user_progress(self, user_id: str, level: int) -> dict:
        """
        Получить прогресс пользователя по конкретному уровню.

        Args:
            user_id: ID пользователя
            level: Номер уровня (1-5)

        Returns:
            Строка из user_level_progress или None
        """
        return level_quest_repo.get_user_progress(user_id, level)


# Глобальный экземпляр
level_quest_interface = LevelQuestInterface()