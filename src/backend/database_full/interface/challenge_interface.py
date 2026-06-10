"""
Интерфейс для работы TESTING_REPORT.md достижениями (ачивками).

Предоставляет внешний API для работы TESTING_REPORT.md достижениями.
Все методы предназначены для вызова из GUI, CLI или REST API.

"""

from typing import List, Dict, Any
from ..service.challenge_service import ChallengeService


class ChallengeInterface:
    """
    Интерфейс для API - вызывает методы ChallengeService.

    Предоставляет упрощенный доступ к функционалу ачивок:
        - Просмотр достижений и прогресса
        - Проверка выполнения
        - Статистика

    Attributes:
        _service (ChallengeService): Сервисный слой для бизнес-логики
    """

    def __init__(self, db_path: str = None):
        """
        Инициализирует интерфейс TESTING_REPORT.md сервисным слоем.

        Args:
            db_path: Путь к БД (опционально)
        """
        self._service = ChallengeService()

    # =====================================================
    # ПОЛУЧЕНИЕ ДАННЫХ
    # =====================================================

    def get_all_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получить все достижения TESTING_REPORT.md прогрессом пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список достижений TESTING_REPORT.md прогрессом

        """
        return self._service.get_achievements(user_id)

    def get_completed(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получить выполненные достижения пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список выполненных достижений

        """
        return self._service.get_completed(user_id)

    def get_completed_count(self, user_id: str) -> int:
        """
        Получить количество выполненных достижений.

        Args:
            user_id: ID пользователя

        Returns:
            Количество выполненных ачивок
        """
        return self._service.get_completed_count(user_id)

    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Получить статистику пользователя по достижениям.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь со статистикой

        Returns структура:
            {
                "plants_grown_to_maturity_perfect": 1,  # идеальных растений
                "death_count": 1,                        # смертей
                "mistake_count": 5,                      # ошибок
                "species_collected": 3,                  # видов
                "consecutive_days": 7,                   # серия дней
                "level": 3,                              # уровень
                "total_achievements": 2                  # получено ачивок
            }

        """
        return self._service.get_statistics(user_id)

    # =====================================================
    # ПРОВЕРКА И ОБНОВЛЕНИЕ
    # =====================================================

    def check_all_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Проверить все достижения пользователя.

        Вызывается после каждого действия.

        Args:
            user_id: ID пользователя

        Returns:
            Список вновь выполненных достижений

        """
        return self._service.check_all(user_id)

    # =====================================================
    # ЗАПИСЬ СОБЫТИЙ (для автоматической проверки)
    # =====================================================

    def record_mistake(self, user_id: str, plant_id: str, mistake_type: str) -> Dict[str, Any]:
        """
        Записать ошибку пользователя.

        Args:
            user_id: ID пользователя
            plant_id: ID растения
            mistake_type: Тип ошибки (overwater, drought, light, cold)

        Returns:
            Результат TESTING_REPORT.md новыми достижениями
        """
        return self._service.record_mistake(user_id, plant_id, mistake_type)

    def record_perfect_growth(self, user_id: str, plant_id: str) -> Dict[str, Any]:
        """
        Записать, что растение выращено без ошибок.

        Args:
            user_id: ID пользователя
            plant_id: ID растения

        Returns:
            Результат TESTING_REPORT.md новыми достижениями
        """
        return self._service.record_perfect_growth(user_id, plant_id)

    def record_plant_death(self, user_id: str, plant_id: str) -> Dict[str, Any]:
        """
        Записать смерть растения.

        Args:
            user_id: ID пользователя
            plant_id: ID растения

        Returns:
            Результат TESTING_REPORT.md новыми достижениями
        """
        return self._service.record_plant_death(user_id, plant_id)

    def record_species_collected(self, user_id: str) -> Dict[str, Any]:
        """
        Записать сбор нового вида.

        Args:
            user_id: ID пользователя

        Returns:
            Результат TESTING_REPORT.md новыми достижениями
        """
        return self._service.record_species_collected(user_id)


# Глобальный экземпляр
challenge_interface = ChallengeInterface()