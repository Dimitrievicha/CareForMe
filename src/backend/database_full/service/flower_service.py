"""
Сервис для управления растениями пользователя.

Содержит бизнес-логику посадки, полива, роста и ухода за растениями.
Также интегрируется TESTING_REPORT.md системой достижений и уровневых заданий.

"""

from typing import Optional, List, Dict, Any
from datetime import date, timedelta
import uuid

from ..repository.plant_repository import PlantRepository
from ..repository.user_repository import UserRepository
from ..repository.mistake_repository import MistakeRepository
from ..repository.challenge_repository import ChallengeRepository
from ..database.db_manager import get_db_manager
from .level_quest_service import level_quest_service


class FlowerService:
    """
    Сервис для управления растениями.

    Обеспечивает полный цикл жизни растения: от посадки до смерти.
    Интегрируется TESTING_REPORT.md системой ачивок и уровневых заданий.

    Attributes:
        plant_repo (PlantRepository): Репозиторий для работы TESTING_REPORT.md растениями
        user_repo (UserRepository): Репозиторий для работы TESTING_REPORT.md пользователями
        mistake_repo (MistakeRepository): Репозиторий для ошибок
        challenge_repo (ChallengeRepository): Репозиторий для ачивок
        db (DatabaseManager): Менеджер БД
    """

    def __init__(self):
        """Инициализирует сервис TESTING_REPORT.md необходимыми репозиториями."""
        self.plant_repo = PlantRepository()
        self.user_repo = UserRepository()
        self.mistake_repo = MistakeRepository()
        self.challenge_repo = ChallengeRepository()
        self.db = get_db_manager()

    def plant_flower(self, user_id: str, species_id: int, custom_name: str = None) -> Dict[str, Any]:
        """
        Посадить новый цветок для пользователя.

        Args:
            user_id: ID пользователя
            species_id: ID вида растения (1=Спатифиллум, 2=Кактус, 3=Фикус)
            custom_name: Пользовательское имя растения (опционально)

        Returns:
            Результат операции TESTING_REPORT.md данными посаженного растения

        Returns структура при успехе:
            {
                "success": True,
                "plant_id": "uuid-...",
                "plant_name": "Мой кактус",
                "species_name": "Кактус Корифанта",
                "species_id": 2
            }

        Returns структура при ошибке:
            {
                "success": False,
                "error": "Нет свободных слотов"
            }

        """

        template = self.plant_repo.get_template_by_species_id(species_id)
        if not template:
            return {"success": False, "error": "Растение не найдено"}


        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"success": False, "error": "Пользователь не найден"}

        if profile['current_plants_count'] >= profile['max_plants_slots']:
            return {"success": False, "error": "Нет свободных слотов"}

        plant_id = str(uuid.uuid4())
        plant_name = custom_name or template['species_name']

        success = self.plant_repo.create_user_plant(plant_id, user_id, template['id'], plant_name)
        if not success:
            return {"success": False, "error": "Ошибка посадки"}

        self.user_repo.update_current_plants_count(user_id, 1)
        self.user_repo.increment_stat(user_id, "total_plants_grown")

        level_quest_service.trigger_quest_check(user_id, "plant")

        return {
            "success": True,
            "plant_id": plant_id,
            "plant_name": plant_name,
            "species_name": template['species_name'],
            "species_id": species_id
        }

    def water_flower(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """
        Полить растение.

        Args:
            plant_id: ID растения пользователя
            user_id: ID пользователя (для проверки прав)

        Returns:
            Результат полива

        Returns структура:
            {
                "success": True,
                "message": "Мой кактус полит!",
                "plant_name": "Мой кактус",
                "was_overwatered": False  # предупреждение о переливе
            }

        """
        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant:
            return {"success": False, "error": "Растение не найдено"}

        if plant['user_id'] != user_id:
            return {"success": False, "error": "Это не ваше растение"}

        if not plant['is_alive']:
            return {"success": False, "error": "Растение мертво. Посадите новое!"}

        today = date.today()
        last_watered = date.fromisoformat(plant['last_watered'])

        if last_watered == today:
            return {"success": False, "error": "Уже полито сегодня"}

        self.plant_repo.water_plant(plant_id)
        self.user_repo.increment_stat(user_id, "total_waterings")

        water_min = plant['water_interval_min']
        days_since = (today - last_watered).days
        was_overwatered = days_since < water_min

        result = {
            "success": True,
            "message": f"{plant['custom_name']} полит!",
            "plant_name": plant['custom_name'],
            "was_overwatered": was_overwatered
        }

        if was_overwatered:
            self.mistake_repo.add_mistake(user_id, plant_id, "overwater")
            result["warning"] = "Осторожно! Возможно, вы поливаете слишком часто."

        level_quest_service.trigger_quest_check(user_id, "water")

        return result

    def set_light_level(self, plant_id: str, user_id: str, light_level: str) -> bool:
        """Сменить уровень освещения растения."""
        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return False
        return self.plant_repo.update_light_level(plant_id, light_level)

    def set_location(self, plant_id: str, user_id: str, location: str) -> bool:
        """Сменить локацию растения."""
        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return False
        return self.plant_repo.update_location(plant_id, location)


    def check_health(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """
        Проверить здоровье растения.

        Анализирует, когда растение было полито в последний раз,
        и определяет статус здоровья.

        Args:
            plant_id: ID растения пользователя
            user_id: ID пользователя (для проверки прав)

        Returns:
            Статус здоровья и предупреждения

        Returns структура:
            {
                "success": True,
                "plant_name": "Мой кактус",
                "health_status": "healthy|wilting|dying",
                "days_since_water": 3,
                "water_interval_min": 3,
                "water_interval_max": 7,
                "warning": "Пора поливать!"  # если status != healthy
            }
        """
        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return {"success": False, "error": "Растение не найдено"}

        if not plant['is_alive']:
            return {
                "success": True,
                "plant_name": plant['custom_name'],
                "is_alive": False,
                "health_status": "dead",
                "death_cause": plant['death_cause'],
                "message": f"{plant['custom_name']} умерло. Посадите новое!"
            }

        today = date.today()
        last_watered = date.fromisoformat(plant['last_watered'])
        days_since = (today - last_watered).days
        water_max = plant['water_interval_max']
        water_min = plant['water_interval_min']

        # Определяем статус здоровья
        if days_since > water_max * 2:
            status = "dying"
            warning = f"{plant['custom_name']} умирает! Срочно полейте!"
        elif days_since > water_max:
            status = "wilting"
            warning = f"{plant['custom_name']} увядает. Пора поливать!"
        else:
            status = "healthy"
            warning = None

        if status != plant['health_status']:
            self.plant_repo.update_health_status(plant_id, status)

            if status == "healthy" and plant['health_status'] in ['wilting', 'dying']:
                level_quest_service.trigger_quest_check(user_id, "heal")

        return {
            "success": True,
            "plant_name": plant['custom_name'],
            "health_status": status,
            "days_since_water": days_since,
            "water_interval_min": water_min,
            "water_interval_max": water_max,
            "warning": warning
        }

    def update_growth(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """
        Обновляет рост растения (вызывается при проверке).

        Args:
            plant_id: ID растения
            user_id: ID пользователя

        Returns:
            Информация об изменении стадии роста
        """
        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return {"success": False, "error": "Растение не найдено"}

        if not plant['is_alive']:
            return {"success": False, "error": "Растение мертво"}

        current_stage = plant['growth_stage']
        current_progress = plant['growth_progress'] or 0.0

        stages = ['seed', 'seedling', 'growing', 'mature', 'flowering']
        stage_thresholds = [0, 25, 50, 75, 100]

        health_status = plant['health_status']
        if health_status == 'healthy':
            increment = 10
        elif health_status == 'wilting':
            increment = 5
        else:
            increment = 2

        new_progress = min(current_progress + increment, 100)
        new_stage = current_stage

        current_index = stages.index(current_stage)
        for i in range(current_index + 1, len(stages)):
            if new_progress >= stage_thresholds[i]:
                new_stage = stages[i]

                if new_stage == 'mature':
                    level_quest_service.trigger_quest_check(user_id, "grow_to_mature")

                    mistakes = self.mistake_repo.get_mistakes_count(user_id)
                    if mistakes == 0:
                        self.plant_repo.mark_perfect_growth(plant_id)

        self.plant_repo.update_growth(plant_id, new_stage, new_progress)

        return {
            "success": True,
            "plant_name": plant['custom_name'],
            "old_stage": current_stage,
            "new_stage": new_stage,
            "old_progress": current_progress,
            "new_progress": new_progress,
            "stage_changed": new_stage != current_stage
        }

    def check_death(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """
        Проверяет, не умерло ли растение, и обрабатывает смерть.

        Args:
            plant_id: ID растения
            user_id: ID пользователя

        Returns:
            Результат проверки
        """
        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return {"success": False, "error": "Растение не найдено"}

        if not plant['is_alive']:
            return {"success": False, "error": "Растение уже мертво"}

        health_check = self.check_health(plant_id, user_id)
        if not health_check['success']:
            return health_check

        if health_check['health_status'] == 'dying':
            cause = "drought"
            self.plant_repo.kill_plant(plant_id, cause)
            self.user_repo.increment_stat(user_id, "total_deaths")
            self.user_repo.update_current_plants_count(user_id, -1)

            self.mistake_repo.add_mistake(user_id, plant_id, cause)

            level_quest_service.trigger_quest_check(user_id, "death")

            return {
                "success": True,
                "plant_name": plant['custom_name'],
                "is_dead": True,
                "death_cause": cause,
                "message": f"{plant['custom_name']} засохло и умерло..."
            }

        return {
            "success": True,
            "is_dead": False
        }

    def revive_plant(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """
        Воскрешает мертвое растение (пересадка заново).

        Args:
            plant_id: ID растения
            user_id: ID пользователя

        Returns:
            Результат воскрешения
        """
        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return {"success": False, "error": "Растение не найдено"}

        if plant['is_alive']:
            return {"success": False, "error": "Растение еще живо!"}

        self.plant_repo.revive_plant(plant_id)
        self.user_repo.update_current_plants_count(user_id, 1)

        return {
            "success": True,
            "plant_name": plant['custom_name'],
            "message": f"{plant['custom_name']} посажено заново!"
        }

    def get_my_garden(self, user_id: str, only_alive: bool = True) -> List[Dict[str, Any]]:
        """
        Получить сад пользователя.

        Args:
            user_id: ID пользователя
            only_alive: Только живые растения

        Returns:
            Список растений пользователя
        """
        return self.plant_repo.get_user_plants(user_id, only_alive)

    def get_plant_details(self, plant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить детальную информацию о растении.

        Args:
            plant_id: ID растения
            user_id: ID пользователя (для проверки прав)

        Returns:
            Данные растения или None
        """
        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if plant and plant['user_id'] == user_id:
            return plant
        return None

    def get_all_growth_stages(self, user_id: str) -> Dict[str, int]:
        """
        Получить статистику по стадиям роста всех растений пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь {стадия: количество}
        """
        plants = self.plant_repo.get_user_plants(user_id, only_alive=True)
        stages = {
            'seed': 0,
            'seedling': 0,
            'growing': 0,
            'mature': 0,
            'flowering': 0
        }

        for plant in plants:
            stage = plant['growth_stage']
            if stage in stages:
                stages[stage] += 1

        return stages


# Глобальный экземпляр
flower_service = FlowerService()