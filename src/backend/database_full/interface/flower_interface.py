"""Интерфейс для работы с растениями"""
from typing import List, Dict, Any, Optional
from ..service.flower_service import FlowerService


class FlowerInterface:
    """Интерфейс для API - вызывает методы FlowerService"""

    def __init__(self, db_path: str = None):
        self._service = FlowerService()

    # ==================== ШАБЛОНЫ ====================

    def get_available_plants(self) -> List[Dict[str, Any]]:
        """Получить список доступных растений"""
        return self._service.get_all_plant_templates()

    def get_plant_info(self, species_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о растении"""
        return self._service.get_plant_template_by_id(species_id)

    # ==================== РАСТЕНИЯ ПОЛЬЗОВАТЕЛЯ ====================

    def get_my_garden(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить сад пользователя (только живые)"""
        return self._service.get_user_plants(user_id, only_alive=True)

    def get_all_user_plants(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить все растения пользователя (включая мёртвые)"""
        return self._service.get_user_plants(user_id, only_alive=False)

    def get_plant_details(self, plant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить детали растения"""
        plant = self._service.get_plant_by_id(plant_id)
        return plant if plant and plant['user_id'] == user_id else None

    # ==================== ДЕЙСТВИЯ ====================

    def plant_flower(self, user_id: str, species_id: int, name: str = None) -> Dict[str, Any]:
        """Посадить цветок"""
        return self._service.plant_flower(user_id, species_id, name)

    def water_flower(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Полить цветок"""
        return self._service.water_flower(plant_id, user_id)

    def check_health(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Проверить здоровье"""
        return self._service.check_health(plant_id, user_id)

    def update_growth(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Обновить рост"""
        return self._service.update_growth(plant_id, user_id)

    def revive_plant(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Воскресить растение"""
        return self._service.revive_plant(plant_id, user_id)

    # ==================== СОВЕТЫ ====================

    def get_care_tips(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Получить советы по уходу"""
        plant = self._service.get_plant_by_id(plant_id)

        if not plant or plant['user_id'] != user_id:
            return {"success": False, "error": "Растение не найдено"}

        tips = plant.get('tips', [])
        if isinstance(tips, str):
            import json
            try:
                tips = json.loads(tips)
            except:
                tips = [tips]

        return {
            "success": True,
            "plant_name": plant['custom_name'],
            "health_status": plant['health_status'],
            "growth_stage": plant['growth_stage'],
            "tips": tips,
            "watering_advice": plant.get('watering_advice', ''),
            "light_advice": plant.get('light_advice', '')
        }