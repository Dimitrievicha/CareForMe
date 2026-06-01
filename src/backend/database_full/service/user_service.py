"""
Сервис пользователя - профиль, уровни, серии.

Содержит бизнес-логику для:
    - Управления уровнями (только через выполнение заданий)
    - Ежедневных серий
    - Слотов для растений
    - Открытия дизайнов


"""

from typing import Optional, Dict, Any, List
from datetime import date
import json

from ..repository.user_repository import UserRepository
from ..database.db_manager import get_db_manager


class UserService:
    """
    Сервис для работы с пользовательскими данными.

    Управляет профилями, уровнями, дизайнами и сериями.
    Уровень повышается только через выполнение заданий (см. LevelQuestService).

    Attributes:
        user_repo (UserRepository): Репозиторий пользователей
        db (DatabaseManager): Менеджер БД для сложных запросов
    """

    def __init__(self):
        """Инициализирует сервис с репозиторием пользователей."""
        self.user_repo = UserRepository()
        self.db = get_db_manager()

    def complete_tutorial(self, user_id: str) -> bool:
        """Отметить обучение пройденным."""
        return self.user_repo.db.execute_update(
            "UPDATE player_profiles SET tutorial_completed = 1 WHERE user_id = ?",
            (user_id,)
        )

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает игровой профиль пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Данные профиля или None
        """
        return self.user_repo.get_profile(user_id)

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получает основную статистику пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь со статистикой

        Returns структура:
            {
                "level": 2,
                "max_plants_slots": 2,
                "current_plants": 1,
                "total_plants_grown": 3,
                "total_waterings": 15,
                "consecutive_days": 5,
                "best_streak": 5
            }
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {
                "level": 1,
                "max_plants_slots": 1,
                "current_plants": 0,
                "total_plants_grown": 0,
                "total_waterings": 0,
                "consecutive_days": 0,
                "best_streak": 0
            }

        return {
            "level": profile['current_level'],
            "max_plants_slots": profile['max_plants_slots'],
            "current_plants": profile['current_plants_count'],
            "total_plants_grown": profile['total_plants_grown'],
            "total_waterings": profile['total_waterings'],
            "consecutive_days": profile['consecutive_days'],
            "best_streak": profile['best_streak']
        }

    def get_current_level(self, user_id: str) -> int:
        """
        Получает текущий уровень пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Уровень (1-5)
        """
        profile = self.user_repo.get_profile(user_id)
        return profile['current_level'] if profile else 1

    def get_level_info(self, user_id: str) -> Dict[str, Any]:
        """
        Получает полную информацию об уровне пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Информация об уровне и следующих заданиях

        Returns структура:
            {
                "current_level": 2,
                "max_level": 5,
                "next_level_quests": {
                    "quest1": {...},
                    "quest2": {...},
                    "quest3": {...}
                }
            }
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"current_level": 1, "max_level": 5, "next_level_quests": None}

        current_level = profile['current_level']

        if current_level >= 5:
            return {
                "current_level": 5,
                "max_level": 5,
                "is_max_level": True
            }

        next_level_quests = self.db.execute_query("""
            SELECT quest1_type, quest1_target, quest1_description,
                   quest2_type, quest2_target, quest2_description,
                   quest3_type, quest3_target, quest3_description
            FROM level_requirements 
            WHERE level = ?
        """, (current_level + 1,))

        return {
            "current_level": current_level,
            "max_level": 5,
            "is_max_level": False,
            "next_level_quests": next_level_quests[0] if next_level_quests else None
        }

    def update_daily_streak(self, user_id: str) -> Dict[str, Any]:
        """
        Обновляет ежедневную серию пользователя.

        Вызывается при каждом входе в игру.
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"success": False}

        today = date.today()
        last_entry = profile['last_entry']

        # ПРЕОБРАЗОВАНИЕ: если last_entry строка, конвертируем в date
        if last_entry and isinstance(last_entry, str):
            from datetime import datetime
            last_entry = datetime.strptime(last_entry, '%Y-%m-%d').date()

        # Проверка: заходил ли уже сегодня
        if last_entry == today:
            return {
                "success": True,
                "consecutive_days": profile['consecutive_days'],
                "best_streak": profile['best_streak'],
                "streak_increased": False
            }

        # Проверка: был ли вчера
        if last_entry and (today - last_entry).days == 1:
            new_streak = profile['consecutive_days'] + 1
        else:
            new_streak = 1  # Сброс серии

        best_streak = max(profile['best_streak'], new_streak)
        self.user_repo.update_streak(user_id, new_streak, best_streak)

        return {
            "success": True,
            "consecutive_days": new_streak,
            "best_streak": best_streak,
            "streak_increased": True
        }

    def get_streak_info(self, user_id: str) -> Dict[str, int]:
        """
        Получает информацию о серии дней.

        Args:
            user_id: ID пользователя

        Returns:
            Информация о серии

        Returns структура:
            {
                "consecutive_days": 5,
                "best_streak": 10
            }
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"consecutive_days": 0, "best_streak": 0}

        return {
            "consecutive_days": profile['consecutive_days'],
            "best_streak": profile['best_streak']
        }

    def get_plant_slots(self, user_id: str) -> Dict[str, int]:
        """
        Получает информацию о слотах для растений.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь с информацией о слотах

        Returns структура:
            {
                "current": 2,      # текущее количество растений
                "max": 5,          # максимум слотов
                "available": 3     # свободных слотов
            }
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"current": 0, "max": 1, "available": 1}

        return {
            "current": profile['current_plants_count'],
            "max": profile['max_plants_slots'],
            "available": profile['max_plants_slots'] - profile['current_plants_count']
        }

    def has_free_slot(self, user_id: str) -> bool:
        """
        Проверяет, есть ли свободный слот для посадки.

        Args:
            user_id: ID пользователя

        Returns:
            True если есть свободный слот
        """
        slots = self.get_plant_slots(user_id)
        return slots['available'] > 0

    def get_unlocked_pots(self, user_id: str) -> List[str]:
        """
        Получает список открытых горшков.

        Args:
            user_id: ID пользователя

        Returns:
            Список ID дизайнов горшков

        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return ["standard"]
        return json.loads(profile['unlocked_pots'])

    def get_unlocked_watering_cans(self, user_id: str) -> List[str]:
        """
        Получает список открытых леек.

        Args:
            user_id: ID пользователя

        Returns:
            Список ID дизайнов леек
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return ["standard"]
        return json.loads(profile['unlocked_watering_cans'])

    def get_current_designs(self, user_id: str) -> Dict[str, str]:
        """
        Получает текущие выбранные дизайны.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь с текущими дизайнами

        Returns структура:
            {
                "pot": "standard",
                "watering_can": "standard"
            }
        """
        profile = self.user_repo.get_profile(user_id)
        if not profile:
            return {"pot": "standard", "watering_can": "standard"}

        return {
            "pot": profile['current_pot'],
            "watering_can": profile['current_watering_can']
        }

    def change_pot(self, user_id: str, pot_id: str) -> Dict[str, Any]:
        """
        Сменить текущий горшок.

        Args:
            user_id: ID пользователя
            pot_id: ID дизайна горшка

        Returns:
            Результат смены горшка

        Returns структура:
            {"success": True} или {"success": False, "error": "Горшок не открыт"}
        """
        unlocked = self.get_unlocked_pots(user_id)
        if pot_id not in unlocked:
            return {"success": False, "error": "Горшок не открыт"}

        success = self.db.execute_update(
            "UPDATE player_profiles SET current_pot = ? WHERE user_id = ?",
            (pot_id, user_id)
        )
        return {"success": success}

    def change_watering_can(self, user_id: str, can_id: str) -> Dict[str, Any]:
        """
        Сменить текущую лейку.

        Args:
            user_id: ID пользователя
            can_id: ID дизайна лейки

        Returns:
            Результат смены лейки
        """
        unlocked = self.get_unlocked_watering_cans(user_id)
        if can_id not in unlocked:
            return {"success": False, "error": "Лейка не открыта"}

        success = self.db.execute_update(
            "UPDATE player_profiles SET current_watering_can = ? WHERE user_id = ?",
            (can_id, user_id)
        )
        return {"success": success}

    def increment_current_plants(self, user_id: str, delta: int = 1) -> bool:
        """
        Изменяет количество текущих растений.

        Используется LevelQuestService при посадке/смерти растения.

        Args:
            user_id: ID пользователя
            delta: На сколько изменить (+1 или -1)

        Returns:
            True при успехе
        """
        return self.user_repo.update_current_plants_count(user_id, delta)

    def increment_stat(self, user_id: str, stat_name: str, delta: int = 1) -> bool:
        """
        Увеличивает статистику пользователя.

        Используется LevelQuestService для отслеживания прогресса заданий.

        Args:
            user_id: ID пользователя
            stat_name: Название статистики
            delta: На сколько увеличить

        Returns:
            True при успехе
        """
        return self.user_repo.increment_stat(user_id, stat_name, delta)

    def unlock_pot(self, user_id: str, pot_id: str) -> bool:
        """
        Открывает новый дизайн горшка.

        Используется LevelQuestService при выдаче награды.

        Args:
            user_id: ID пользователя
            pot_id: ID дизайна горшка

        Returns:
            True при успехе
        """
        return self.user_repo.unlock_pot(user_id, pot_id)

    def unlock_watering_can(self, user_id: str, can_id: str) -> bool:
        """
        Открывает новый дизайн лейки.

        Используется LevelQuestService при выдаче награды.

        Args:
            user_id: ID пользователя
            can_id: ID дизайна лейки

        Returns:
            True при успехе
        """
        return self.user_repo.unlock_watering_can(user_id, can_id)

    def add_plant_slot(self, user_id: str) -> bool:
        """
        Добавляет один слот для растения.

        Используется LevelQuestService при выдаче награды.

        Args:
            user_id: ID пользователя

        Returns:
            True при успехе
        """
        return self.user_repo.update_plant_slots(user_id, 1)


# Глобальный экземпляр для удобства
user_service = UserService()