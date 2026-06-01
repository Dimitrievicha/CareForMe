"""
Интерфейс для работы с советами (вызывается из API)
"""

from ..service.tips_service import tips_service


class TipsInterface:
    """Интерфейс для API — только вызов сервиса, никакой логики."""

    def get_all_tips(self):
        """Получить все советы."""
        return tips_service.get_all_tips()

    def get_positive_tips(self):
        """Получить позитивные советы."""
        return tips_service.get_positive_tips()

    def get_tip_by_type(self, tip_type: str):
        """Получить совет по типу."""
        return tips_service.get_tip_by_type(tip_type)

    def get_plant_tips(self, species_id: int):
        """Получить советы для растения."""
        return tips_service.get_plant_tips(species_id)


# Глобальный экземпляр
tips_interface = TipsInterface()