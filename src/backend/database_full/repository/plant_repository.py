"""
Репозиторий для работы с растениями.

Содержит методы для работы с таблицами:
    - plant_templates: шаблоны растений (справочник)
    - user_plants: растения конкретных пользователей

"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class PlantRepository(BaseRepository):
    """
    Репозиторий для таблиц plant_templates и user_plants.

    Обрабатывает все операции с растениями:
        - Получение шаблонов растений
        - Посадка, полив, рост, смерть растений
    """

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """
        Получает все шаблоны растений, отсортированные по sort_order.

        Returns:
            Список всех шаблонов растений
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
        """
        Получает шаблон растения по species_id.

        Args:
            species_id: ID вида растения (1=Спатифиллюм, 2=Кактус, 3=Фикус)

        Returns:
            Данные шаблона или None
        """
        result = self.db.execute_query(
            "SELECT * FROM plant_templates WHERE species_id = ?",
            (species_id,)
        )
        return result[0] if result else None

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает шаблон растения по внутреннему UUID.

        Args:
            template_id: UUID шаблона

        Returns:
            Данные шаблона или None
        """
        return self.get_by_id("plant_templates", "id", template_id)

    def create_user_plant(self, plant_id: str, user_id: str, template_id: str, custom_name: str) -> bool:
        """
        Создает новое растение пользователя (посадка).

        Args:
            plant_id: UUID нового растения
            user_id: ID пользователя
            template_id: ID шаблона растения
            custom_name: Пользовательское имя растения

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            INSERT INTO user_plants (id, user_id, template_id, custom_name, growth_stage)
            VALUES (?, ?, ?, ?, 'seed')
        """, (plant_id, user_id, template_id, custom_name))

    def get_user_plants(self, user_id: str, only_alive: bool = True) -> List[Dict[str, Any]]:
        """
        Получает растения пользователя.

        Args:
            user_id: ID пользователя
            only_alive: Если True, только живые растения

        Returns:
            Список растений с данными из шаблона
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
        """
        Получает растение пользователя по UUID.

        Args:
            plant_id: UUID растения

        Returns:
            Данные растения или None
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
        """
        Обновляет дату последнего полива растения.

        Args:
            plant_id: UUID растения

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants SET last_watered = CURRENT_DATE, last_checked = CURRENT_DATE 
            WHERE id = ?
        """, (plant_id,))

    def update_health_status(self, plant_id: str, status: str) -> bool:
        """
        Обновляет статус здоровья растения.

        Args:
            plant_id: UUID растения
            status: Статус (healthy, wilting, overwatered, dying, dead)

        Returns:
            True при успехе
        """
        return self.db.execute_update(
            "UPDATE user_plants SET health_status = ? WHERE id = ?",
            (status, plant_id)
        )

    def update_growth(self, plant_id: str, growth_stage: str, growth_progress: float) -> bool:
        """
        Обновляет стадию роста и прогресс.

        Args:
            plant_id: UUID растения
            growth_stage: Стадия (seed, seedling, growing, mature, flowering)
            growth_progress: Прогресс (0-100)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants SET growth_stage = ?, growth_progress = ? WHERE id = ?
        """, (growth_stage, growth_progress, plant_id))

    def increment_growth_progress(self, plant_id: str, increment: float) -> bool:
        """
        Увеличивает прогресс роста на указанное значение.

        Args:
            plant_id: UUID растения
            increment: Прирост прогресса (обычно 10-20%)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants SET growth_progress = growth_progress + ? WHERE id = ?
        """, (increment, plant_id))

    def mark_perfect_growth(self, plant_id: str) -> bool:
        """
        Отмечает растение как выращенное без критических ошибок.

        Используется для ачивки "Заботливый родитель".

        Args:
            plant_id: UUID растения

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants SET has_perfect_growth = 1 WHERE id = ?
        """, (plant_id,))

    def kill_plant(self, plant_id: str, cause: str) -> bool:
        """
        Помечает растение как мертвое.

        Args:
            plant_id: UUID растения
            cause: Причина смерти (overwater, drought, neglect)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants 
            SET is_alive = 0, death_cause = ?, death_date = CURRENT_DATE, 
                times_reborn = times_reborn + 1
            WHERE id = ?
        """, (cause, plant_id))

    def revive_plant(self, plant_id: str) -> bool:
        """
        Воскрешает мертвое растение (пересадка заново).

        Args:
            plant_id: UUID растения

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants 
            SET is_alive = 1, health_status = 'healthy', growth_stage = 'seed', 
                growth_progress = 0, death_cause = NULL, death_date = NULL, 
                last_watered = CURRENT_DATE, last_checked = CURRENT_DATE
            WHERE id = ?
        """, (plant_id,))

    def increment_times_flowered(self, plant_id: str) -> bool:
        """
        Увеличивает счетчик цветений растения.

        Args:
            plant_id: UUID растения

        Returns:
            True при успехе
        """
        return self.db.execute_update(
            "UPDATE user_plants SET times_flowered = times_flowered + 1 WHERE id = ?",
            (plant_id,)
        )

    def get_dead_plants(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает мертвые растения пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список мертвых растений с причиной смерти
        """
        return self.db.execute_query("""
            SELECT up.*, pt.species_name, pt.nickname as plant_nickname, up.death_cause
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.user_id = ? AND up.is_alive = 0
            ORDER BY up.death_date DESC
        """, (user_id,))

    def get_plants_by_stage(self, user_id: str, stage: str) -> List[Dict[str, Any]]:
        """
        Получает растения пользователя на определенной стадии роста.

        Args:
            user_id: ID пользователя
            stage: Стадия (seed, seedling, growing, mature, flowering)

        Returns:
            Список растений на указанной стадии
        """
        return self.db.execute_query("""
            SELECT up.*, pt.species_name
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.user_id = ? AND up.growth_stage = ? AND up.is_alive = 1
        """, (user_id, stage))