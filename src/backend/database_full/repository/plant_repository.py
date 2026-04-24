"""Репозиторий для работы с растениями.

Содержит методы для работы с таблицами:
    - plant_templates: шаблоны растений (справочник)
    - user_plants: растения конкретных пользователей

Пример:
    >>> repo = PlantRepository()
    >>> templates = repo.get_all_templates()
    >>> my_plants = repo.get_user_plants("user123")
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class PlantRepository(BaseRepository):
    """Репозиторий для таблиц plant_templates и user_plants."""

    # ==================== PLANT TEMPLATES ====================

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Получает все шаблоны растений, отсортированные по sort_order.

        :return: Список всех шаблонов растений
        :rtype: List[Dict[str, Any]]

        :example:
            >>> repo = PlantRepository()
            >>> templates = repo.get_all_templates()
            >>> for t in templates:
            ...     print(t['species_name'])
        """
        return self.db.execute_query("""
            SELECT species_id, species_name, nickname, description, character_trait,
                   water_interval_min, water_interval_max, light_requirement, humidity_preference,
                   watering_advice, light_advice, flowering_conditions, temp_advice,
                   tips, symptoms, sort_order
            FROM plant_templates 
            ORDER BY sort_order
        """)

    def get_template_by_species_id(self, species_id: int) -> Optional[Dict[str, Any]]:
        """Получает шаблон растения по species_id.

        :param species_id: ID вида растения
        :type species_id: int
        :return: Данные шаблона или None
        :rtype: Optional[Dict[str, Any]]
        """
        result = self.db.execute_query(
            "SELECT * FROM plant_templates WHERE species_id = ?",
            (species_id,)
        )
        return result[0] if result else None

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Получает шаблон растения по внутреннему ID.

        :param template_id: UUID шаблона
        :type template_id: str
        :return: Данные шаблона или None
        :rtype: Optional[Dict[str, Any]]
        """
        return self.get_by_id("plant_templates", "id", template_id)

    # ==================== USER PLANTS ====================

    def create_user_plant(self, plant_id: str, user_id: str, template_id: str, custom_name: str) -> bool:
        """Создает новое растение пользователя.

        :param plant_id: UUID растения
        :type plant_id: str
        :param user_id: ID пользователя
        :type user_id: str
        :param template_id: ID шаблона растения
        :type template_id: str
        :param custom_name: Пользовательское имя растения
        :type custom_name: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            INSERT INTO user_plants (id, user_id, template_id, custom_name, growth_stage)
            VALUES (?, ?, ?, ?, 'seed')
        """, (plant_id, user_id, template_id, custom_name))

    def get_user_plants(self, user_id: str, only_alive: bool = True) -> List[Dict[str, Any]]:
        """Получает растения пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :param only_alive: Если True, только живые растения
        :type only_alive: bool
        :return: Список растений
        :rtype: List[Dict[str, Any]]
        """
        alive_filter = "AND up.is_alive = 1" if only_alive else ""
        return self.db.execute_query(f"""
            SELECT up.*, pt.species_name, pt.nickname as plant_nickname, pt.character_trait,
                   pt.water_interval_min, pt.water_interval_max, pt.light_requirement,
                   pt.watering_advice, pt.light_advice, pt.tips, pt.symptoms
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.user_id = ? {alive_filter}
            ORDER BY up.acquired_at DESC
        """, (user_id,))

    def get_user_plant_by_id(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """Получает растение пользователя по ID.

        :param plant_id: UUID растения
        :type plant_id: str
        :return: Данные растения или None
        :rtype: Optional[Dict[str, Any]]
        """
        result = self.db.execute_query("""
            SELECT up.*, pt.species_name, pt.nickname as plant_nickname, pt.character_trait,
                   pt.water_interval_min, pt.water_interval_max, pt.light_requirement,
                   pt.watering_advice, pt.light_advice, pt.tips, pt.symptoms
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.id = ?
        """, (plant_id,))
        return result[0] if result else None

    def water_plant(self, plant_id: str) -> bool:
        """Обновляет дату последнего полива растения.

        :param plant_id: UUID растения
        :type plant_id: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE user_plants SET last_watered = CURRENT_DATE, last_checked = CURRENT_DATE WHERE id = ?
        """, (plant_id,))

    def update_health_status(self, plant_id: str, status: str) -> bool:
        """Обновляет статус здоровья растения.

        :param plant_id: UUID растения
        :type plant_id: str
        :param status: Статус (healthy, wilting, overwatered, dying, dead)
        :type status: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update(
            "UPDATE user_plants SET health_status = ? WHERE id = ?",
            (status, plant_id)
        )

    def update_growth(self, plant_id: str, growth_stage: str, growth_progress: float) -> bool:
        """Обновляет стадию роста и прогресс.

        :param plant_id: UUID растения
        :type plant_id: str
        :param growth_stage: Стадия (seed, seedling, growing, mature, flowering)
        :type growth_stage: str
        :param growth_progress: Прогресс (0-100)
        :type growth_progress: float
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE user_plants SET growth_stage = ?, growth_progress = ? WHERE id = ?
        """, (growth_stage, growth_progress, plant_id))

    def increment_growth_progress(self, plant_id: str, increment: float) -> bool:
        """Увеличивает прогресс роста на указанное значение.

        :param plant_id: UUID растения
        :type plant_id: str
        :param increment: Прирост прогресса
        :type increment: float
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE user_plants SET growth_progress = growth_progress + ? WHERE id = ?
        """, (increment, plant_id))

    def kill_plant(self, plant_id: str, cause: str) -> bool:
        """Помечает растение как мертвое.

        :param plant_id: UUID растения
        :type plant_id: str
        :param cause: Причина смерти
        :type cause: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE user_plants 
            SET is_alive = 0, death_cause = ?, death_date = CURRENT_DATE, times_reborn = times_reborn + 1
            WHERE id = ?
        """, (cause, plant_id))

    def revive_plant(self, plant_id: str) -> bool:
        """Воскрешает мертвое растение (сбрасывает все параметры).

        :param plant_id: UUID растения
        :type plant_id: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update("""
            UPDATE user_plants 
            SET is_alive = 1, health_status = 'healthy', growth_stage = 'seed', growth_progress = 0,
                death_cause = NULL, death_date = NULL, last_watered = CURRENT_DATE, last_checked = CURRENT_DATE
            WHERE id = ?
        """, (plant_id,))

    def increment_times_flowered(self, plant_id: str) -> bool:
        """Увеличивает счетчик цветений растения.

        :param plant_id: UUID растения
        :type plant_id: str
        :return: True при успехе
        :rtype: bool
        """
        return self.db.execute_update(
            "UPDATE user_plants SET times_flowered = times_flowered + 1 WHERE id = ?",
            (plant_id,)
        )

    def get_dead_plants(self, user_id: str) -> List[Dict[str, Any]]:
        """Получает мертвые растения пользователя.

        :param user_id: ID пользователя
        :type user_id: str
        :return: Список мертвых растений
        :rtype: List[Dict[str, Any]]
        """
        return self.db.execute_query("""
            SELECT up.*, pt.species_name, pt.nickname as plant_nickname, up.death_cause
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.user_id = ? AND up.is_alive = 0
            ORDER BY up.death_date DESC
        """, (user_id,))