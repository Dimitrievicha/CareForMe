"""Сервис растений - посадка, полив, рост"""
from typing import Optional, List, Dict, Any
from datetime import date
import uuid

from ..repository.plant_repository import PlantRepository
from ..repository.user_repository import UserRepository


class FlowerService:
    def __init__(self):
        self.plant_repo = PlantRepository()
        self.user_repo = UserRepository()

    def get_user_plants(self, user_id: str, only_alive: bool = True) -> List[Dict[str, Any]]:
        """Получить растения пользователя"""
        return self.plant_repo.get_user_plants(user_id, only_alive)

    def get_all_plant_templates(self) -> List[Dict[str, Any]]:
        """Получить все шаблоны растений"""
        return self.plant_repo.get_all_templates()

    def get_plant_template_by_id(self, species_id: int) -> Optional[Dict[str, Any]]:
        """Получить шаблон по species_id"""
        return self.plant_repo.get_template_by_species_id(species_id)

    def get_my_garden(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить сад пользователя (живые растения)"""
        return self.plant_repo.get_user_plants(user_id, only_alive=True)

    def get_all_user_plants(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить ВСЕ растения пользователя (включая мёртвые)"""
        return self.plant_repo.get_user_plants(user_id, only_alive=False)

    def get_plant_by_id(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """Получить растение по ID"""
        return self.plant_repo.get_user_plant_by_id(plant_id)

    def get_dead_plants(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить мёртвые растения пользователя"""
        return self.plant_repo.get_dead_plants(user_id)

    def plant_flower(self, user_id: str, species_id: int, custom_name: str = None) -> Dict[str, Any]:
        """Посадить новый цветок"""

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

        return {
            "success": True,
            "plant_id": plant_id,
            "plant_name": plant_name,
            "species_name": template['species_name']
        }

    def water_flower(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Полить растение"""

        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant:
            return {"success": False, "error": "Растение не найдено"}

        if plant['user_id'] != user_id:
            return {"success": False, "error": "Это не ваше растение"}

        if not plant['is_alive']:
            return {"success": False, "error": "Растение мертво"}

        today = date.today()
        last_watered = date.fromisoformat(plant['last_watered'])

        if last_watered == today:
            return {"success": False, "error": "Уже полито сегодня"}

        self.plant_repo.water_plant(plant_id)
        self.user_repo.increment_stat(user_id, "total_waterings")

        return {"success": True, "message": f"{plant['custom_name']} полит!"}

    def check_health(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Проверить здоровье растения"""

        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return {"success": False, "error": "Растение не найдено"}

        today = date.today()
        last_watered = date.fromisoformat(plant['last_watered'])
        days_since = (today - last_watered).days
        water_max = plant['water_interval_max']

        if days_since > water_max * 2:
            status = "dying"
            warning = f"{plant['custom_name']} умирает! Срочно полей!"
        elif days_since > water_max:
            status = "wilting"
            warning = f"{plant['custom_name']} увядает. Пора поливать!"
        else:
            status = "healthy"
            warning = None

        if status != plant['health_status']:
            self.plant_repo.update_health_status(plant_id, status)

        return {
            "success": True,
            "plant_name": plant['custom_name'],
            "health_status": status,
            "days_since_water": days_since,
            "water_interval_min": plant['water_interval_min'],
            "water_interval_max": water_max,
            "warning": warning
        }

    def update_growth(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Обновить стадию роста растения"""

        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return {"success": False, "error": "Растение не найдено"}

        if not plant['is_alive']:
            return {"success": False, "error": "Растение мертво"}

        stages = ['seed', 'seedling', 'growing', 'mature', 'flowering']

        if plant['growth_stage'] not in stages:
            return {"success": False, "error": "Неизвестная стадия роста"}

        current_idx = stages.index(plant['growth_stage'])

        if current_idx == len(stages) - 1:
            return {"success": True, "leveled_up": False, "message": "Растение достигло максимальной стадии"}

        if plant['health_status'] == 'healthy':
            progress_increase = 10
        elif plant['health_status'] == 'wilting':
            progress_increase = 5
        else:
            progress_increase = 2

        new_progress = plant['growth_progress'] + progress_increase

        if new_progress >= 100:
            next_stage = stages[current_idx + 1]
            self.plant_repo.update_growth(plant_id, next_stage, 0)

            if next_stage == 'flowering':
                self.plant_repo.increment_times_flowered(plant_id)

            return {
                "success": True,
                "leveled_up": True,
                "new_stage": next_stage,
                "message": f"{plant['custom_name']} перешёл на стадию {next_stage}!"
            }
        else:
            self.plant_repo.increment_growth_progress(plant_id, progress_increase)
            return {
                "success": True,
                "leveled_up": False,
                "progress": new_progress,
                "message": f"Рост продолжается: {int(new_progress)}%"
            }

    def kill_plant(self, plant_id: str, user_id: str, cause: str) -> bool:
        """Убить растение (при критической ошибке)"""

        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return False

        success = self.plant_repo.kill_plant(plant_id, cause)

        if success:
            self.user_repo.update_current_plants_count(user_id, -1)
            self.user_repo.increment_stat(user_id, "total_deaths")

        return success

    def revive_plant(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Воскресить растение (посадить заново)"""

        plant = self.plant_repo.get_user_plant_by_id(plant_id)
        if not plant or plant['user_id'] != user_id:
            return {"success": False, "error": "Растение не найдено"}

        profile = self.user_repo.get_profile(user_id)
        if profile['current_plants_count'] >= profile['max_plants_slots']:
            return {"success": False, "error": "Нет свободных слотов"}

        success = self.plant_repo.revive_plant(plant_id)

        if success:
            self.user_repo.update_current_plants_count(user_id, 1)

        return {"success": success, "message": "Растение воскрешено!"}