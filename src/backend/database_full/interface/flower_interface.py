"""API интерфейс для работы с растениями.

Предоставляет внешний API для вызовов из приложения.
Служит прослойкой между клиентским кодом и FlowerService.
"""

from typing import List, Dict, Any, Optional
from ..service.flower_service import FlowerService


class FlowerInterface:
    """Интерфейс для API - вызывает методы FlowerService.

    Все методы этого класса предназначены для вызова из внешнего кода.

    Attributes:
        _service (FlowerService): Сервисный слой для бизнес-логики
    """

    def __init__(self, db_path: str = None):
        """Инициализирует интерфейс с сервисным слоем.

        :param db_path: Путь к БД (опционально)
        :type db_path: str, optional
        """
        self._service = FlowerService()

    def get_my_garden(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить сад пользователя (только живые растения).

        :param user_id: ID пользователя
        :type user_id: str
        :return: Список живых растений пользователя
        :rtype: List[Dict[str, Any]]

        :example:
            >>> interface = FlowerInterface()
            >>> plants = interface.get_my_garden("user123")
            >>> for p in plants:
            ...     print(f"{p['custom_name']} - {p['health_status']}")
        """
        return self._service.get_user_plants(user_id, only_alive=True)

    def plant_flower(self, user_id: str, species_id: int, name: str = None) -> Dict[str, Any]:
        """Посадить новый цветок.

        :param user_id: ID пользователя
        :type user_id: str
        :param species_id: ID вида растения (из каталога)
        :type species_id: int
        :param name: Пользовательское имя (если не указано, используется видовое)
        :type name: str, optional
        :return: Результат посадки
        :rtype: Dict[str, Any]

        :example:
            >>> result = interface.plant_flower("user123", 1, "Мой кактус")
            >>> if result['success']:
            ...     print(f"Растение посажено! ID: {result['plant_id']}")
        """
        return self._service.plant_flower(user_id, species_id, name)

    def water_flower(self, plant_id: str, user_id: str) -> Dict[str, Any]:
        """Полить цветок.

        :param plant_id: ID растения
        :type plant_id: str
        :param user_id: ID пользователя (для проверки прав)
        :type user_id: str
        :return: Результат полива
        :rtype: Dict[str, Any]
        """
        return self._service.water_flower(plant_id, user_id)

    def get_plant_details(self, plant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить детальную информацию о растении.

        :param plant_id: ID растения
        :type plant_id: str
        :param user_id: ID пользователя (для проверки прав)
        :type user_id: str
        :return: Данные растения или None
        :rtype: Optional[Dict[str, Any]]
        """
        plant = self._service.get_plant_by_id(plant_id)
        return plant if plant and plant['user_id'] == user_id else None