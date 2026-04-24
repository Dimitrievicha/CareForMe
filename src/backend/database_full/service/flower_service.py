"""Сервис для управления растениями пользователя.

Содержит бизнес-логику посадки, полива, роста и ухода за растениями.

Пример:
    >>> service = FlowerService()
    >>> result = service.plant_flower("user_123", 1, "Мой кактус")
    >>> if result['success']:
    ...     print(f"Посажен цветок: {result['plant_name']}")
"""

from typing import Optional, List, Dict, Any
from datetime import date
import uuid

from ..repository.plant_repository import PlantRepository
from ..repository.user_repository import UserRepository


class FlowerService:
    """Сервис для управления растениями.

    Обеспечивает полный цикл жизни растения: от посадки до смерти.

    Attributes:
        plant_repo (PlantRepository): Репозиторий для работы с растениями
        user_repo (UserRepository): Репозиторий для работы с пользователями
    """

    def __init__(self):
        """Инициализирует сервис с необходимыми репозиториями."""
        self.plant_repo = PlantRepository()
        self.user_repo = UserRepository()

    def plant_flower(self, user_id: str, species_id: int, custom_name: str = None) -> Dict[str, Any]:
        """Посадить новый цветок для пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param species_id: ID вида растения (из plant_templates)
        :type species_id: int
        :param custom_name: Пользовательское имя растения (опционально)
        :type custom_name: str, optional
        :return: Результат операции с данными посаженного растения
        :rtype: Dict[str, Any]

        :returns: Успешный результат::
            {
                "success": True,
                "plant_id": "uuid",
                "plant_name": "Мой кактус",
                "species_name": "Кактус"
            }

        :returns: Ошибка::
            {
                "success": False,
                "error": "Нет свободных слотов"
            }

        :example:
            >>> service = FlowerService()
            >>> result = service.plant_flower("user123", 1, "Пушистик")
            >>> print(result['success'])
            True
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

        return {
            "success": True,
            "plant_id": plant_id,
            "plant_name": plant_name,
            "species_name": template['species_name']
        }

    def water_flower(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Полить растение.

        :param plant_id: ID растения пользователя
        :type plant_id: str
        :param user_id: ID пользователя (для проверки прав)
        :type user_id: str
        :return: Результат полива
        :rtype: Dict[str, Any]

        :example:
            >>> result = service.water_flower("plant123", "user123")
            >>> if result['success']:
            ...     print(result['message'])
            Мой кактус полит!
        """
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
        """Проверить здоровье растения.

        Анализирует, когда растение было полито в последний раз,
        и определяет статус здоровья.

        :param plant_id: ID растения пользователя
        :type plant_id: str
        :param user_id: ID пользователя
        :type user_id: str
        :return: Статус здоровья и предупреждения
        :rtype: Dict[str, Any]

        :returns::
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