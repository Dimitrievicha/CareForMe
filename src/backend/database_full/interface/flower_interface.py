"""
API интерфейс для работы с растениями.

Предоставляет внешний API для вызовов из приложения (GUI, CLI, REST API).
Служит прослойкой между клиентским кодом и FlowerService.
"""

from typing import List, Dict, Any, Optional
from ..service.flower_service import FlowerService


class FlowerInterface:
    """
    Интерфейс для работы с растениями.

    Все методы этого класса предназначены для вызова из внешнего кода.
    Предоставляет упрощенный API для работы с растениями пользователя.

    Attributes:
        _service (FlowerService): Сервисный слой для бизнес-логики
    """

    def __init__(self, db_path: str = None):
        """
        Инициализирует интерфейс с сервисным слоем.

        Args:
            db_path: Путь к БД (опционально, для тестирования)
        """
        self._service = FlowerService()


    def get_my_garden(self, user_id: str, only_alive: bool = True) -> List[Dict[str, Any]]:
        """
        Получить сад пользователя.

        Args:
            user_id: ID пользователя
            only_alive: Если True, только живые растения

        Returns:
            Список растений пользователя

        """
        return self._service.get_my_garden(user_id, only_alive)

    def plant_flower(self, user_id: str, species_id: int, name: str = None) -> Dict[str, Any]:
        """
        Посадить новый цветок.

        Args:
            user_id: ID пользователя
            species_id: ID вида растения (1=Спатифиллюм, 2=Кактус, 3=Фикус)
            name: Пользовательское имя (если не указано, используется видовое)

        Returns:
            Результат посадки
        """
        return self._service.plant_flower(user_id, species_id, name)

    def water_flower(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """
        Полить цветок.

        Args:
            plant_id: ID растения
            user_id: ID пользователя (для проверки прав)

        Returns:
            Результат полива
        """
        return self._service.water_flower(plant_id, user_id)

    def check_health(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """
        Проверить здоровье растения.

        Args:
            plant_id: ID растения
            user_id: ID пользователя

        Returns:
            Статус здоровья и рекомендации
        """
        return self._service.check_health(plant_id, user_id)

    def get_plant_details(self, plant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить детальную информацию о растении.

        Args:
            plant_id: ID растения
            user_id: ID пользователя (для проверки прав)

        Returns:
            Данные растения или None

        """
        return self._service.get_plant_details(plant_id, user_id)


    def update_growth(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """
        Обновить рост растения (обычно вызывается при проверке).

        Args:
            plant_id: ID растения
            user_id: ID пользователя

        Returns:
            Информация об изменении стадии роста
        """
        return self._service.update_growth(plant_id, user_id)

    def get_growth_stats(self, user_id: str) -> Dict[str, int]:
        """
        Получить статистику по стадиям роста.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь {стадия: количество}
        """
        return self._service.get_all_growth_stages(user_id)

    def get_available_plants(self) -> List[Dict[str, Any]]:
        """
        Получить список доступных для посадки растений.

        Returns:
            Список шаблонов растений
        """
        from ..repository.plant_repository import PlantRepository
        repo = PlantRepository()
        return repo.get_all_templates()

flower_interface = FlowerInterface()