"""
Сервис достижений (ачивок) - отслеживание прогресса и выполнение.

Содержит бизнес-логику для:
    - отслеживания прогресса достижений
    - проверки условий выполнения ачивок
    - учета ошибок пользователей

"""

from typing import List, Dict, Any

from ..repository.challenge_repository import ChallengeRepository
from ..repository.mistake_repository import MistakeRepository
from ..repository.user_repository import UserRepository
from ..repository.plant_repository import PlantRepository


class ChallengeService:
    """
    Сервис для работы с достижениями (ачивками).

    Ачивки служат для:
        - Коллекционирования
        - Отслеживания прогресса игрока
        - Разблокировки условия для ачивки "Страж флоры" (на 5 уровне)

    Attributes:
        challenge_repo (ChallengeRepository): Репозиторий достижений
        mistake_repo (MistakeRepository): Репозиторий ошибок
        user_repo (UserRepository): Репозиторий пользователей
        plant_repo (PlantRepository): Репозиторий растений
    """

    def __init__(self):
        """Инициализирует сервис с необходимыми репозиториями."""
        self.challenge_repo = ChallengeRepository()
        self.mistake_repo = MistakeRepository()
        self.user_repo = UserRepository()
        self.plant_repo = PlantRepository()

    def get_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает все достижения с прогрессом пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список достижений с прогрессом

        Returns структура:
            [
                {
                    "id": "uuid",
                    "name": "Заботливый родитель",
                    "description": "...",
                    "current_progress": 0,
                    "is_completed": False,
                    "completed_at": None
                },
                ...
            ]
        """
        return self.challenge_repo.get_user_achievements(user_id)

    def get_completed(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает выполненные достижения пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список выполненных достижений с датами
        """
        return self.challenge_repo.get_completed_achievements(user_id)

    def get_completed_count(self, user_id: str) -> int:
        """
        Получает количество выполненных достижений.

        Args:
            user_id: ID пользователя

        Returns:
            Количество выполненных ачивок
        """
        return len(self.get_completed(user_id))

    def _get_progress(self, user_id: str, req_type: str) -> int:
        """
        Внутренний метод для получения прогресса по типу требования.

        Args:
            user_id: ID пользователя
            req_type: Тип требования

        Returns:
            Текущий прогресс

        Типы требований и соответствующие проверки:
            - grow_to_maturity_perfect: растение без ошибок до зрелости
            - first_wither: первая смерть растения
            - first_negative_effect: первый негативный эффект (ошибка)
            - grow_all_species: все 3 вида цветов до зрелости
            - daily_streak: серия дней подряд
            - reach_level: достигнут уровень X
        """
        if req_type == 'grow_to_maturity_perfect':
            return self.challenge_repo.check_grow_to_maturity_perfect(user_id)

        elif req_type == 'first_wither':
            return self.challenge_repo.check_first_wither(user_id)

        elif req_type == 'first_negative_effect':
            return self.challenge_repo.check_first_negative_effect(user_id)

        elif req_type == 'grow_all_species':
            return self.challenge_repo.check_species_collected(user_id)

        elif req_type == 'daily_streak':
            return self.challenge_repo.get_consecutive_days(user_id)

        elif req_type == 'reach_level':
            return self.challenge_repo.get_level(user_id)

        return 0

    def check_all(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Проверяет все достижения и отмечает выполненные.

        Вызывается после каждого действия (полив, посадка, ошибка и т.д.)

        Args:
            user_id: ID пользователя

        Returns:
            Список вновь выполненных достижений
        """
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

    def record_mistake(self, user_id: str, plant_id: str, mistake_type: str) -> Dict[str, Any]:
        """
        Записывает ошибку пользователя и проверяет достижения.

        Args:
            user_id: ID пользователя
            plant_id: ID растения
            mistake_type: Тип ошибки (overwater, drought, light, cold)

        Returns:
            Результат с новыми достижениями

        Returns структура:
            {
                "success": True,
                "mistake_type": "overwater",
                "new_achievements": [...]
            }

        """
        self.mistake_repo.add_mistake(user_id, plant_id, mistake_type)

        self.user_repo.increment_stat(user_id, "total_mistakes")

        completed = self.check_all(user_id)

        return {
            "success": True,
            "mistake_type": mistake_type,
            "new_achievements": completed
        }

    def record_perfect_growth(self, user_id: str, plant_id: str) -> Dict[str, Any]:
        """
        Записывает, что растение выращено без ошибок.

        Вызывается, когда растение достигает стадии mature без ошибок.

        Args:
            user_id: ID пользователя
            plant_id: ID растения

        Returns:
            Результат с новыми достижениями
        """
        self.plant_repo.mark_perfect_growth(plant_id)

        completed = self.check_all(user_id)

        return {
            "success": True,
            "new_achievements": completed
        }

    def record_plant_death(self, user_id: str, plant_id: str) -> Dict[str, Any]:
        """
        Записывает смерть растения и проверяет достижения.

        Args:
            user_id: ID пользователя
            plant_id: ID растения

        Returns:
            Результат с новыми достижениями
        """
        completed = self.check_all(user_id)

        return {
            "success": True,
            "new_achievements": completed
        }

    def record_species_collected(self, user_id: str) -> Dict[str, Any]:
        """
        Записывает сбор нового вида и проверяет достижения.

        Args:
            user_id: ID пользователя

        Returns:
            Результат с новыми достижениями
        """
        completed = self.check_all(user_id)

        return {
            "success": True,
            "new_achievements": completed
        }

    def record_daily_streak(self, user_id: str, streak: int) -> Dict[str, Any]:
        """
        Записывает обновление ежедневной серии и проверяет достижения.

        Args:
            user_id: ID пользователя
            streak: Текущая серия дней

        Returns:
            Результат с новыми достижениями
        """
        completed = self.check_all(user_id)

        return {
            "success": True,
            "streak": streak,
            "new_achievements": completed
        }

    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Получает полную статистику пользователя по достижениям.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь со статистикой

        Returns структура:
            {
                "plants_grown_to_maturity_perfect": 1,  # идеальных растений
                "death_count": 1,                        # количество смертей
                "mistake_count": 5,                      # количество ошибок
                "species_collected": 3,                  # собранных видов (макс 3)
                "consecutive_days": 7,                   # серия дней
                "level": 3,                              # текущий уровень
                "total_achievements": 2                  # получено ачивок
            }
        """
        return {
            "plants_grown_to_maturity_perfect": self.challenge_repo.check_grow_to_maturity_perfect(user_id),
            "death_count": self.challenge_repo.check_first_wither(user_id),
            "mistake_count": self.mistake_repo.get_mistakes_count(user_id),
            "species_collected": self.challenge_repo.check_species_collected(user_id),
            "consecutive_days": self.challenge_repo.get_consecutive_days(user_id),
            "level": self.challenge_repo.get_level(user_id),
            "total_achievements": len(self.challenge_repo.get_completed_achievements(user_id))
        }


# Глобальный экземпляр
challenge_service = ChallengeService()