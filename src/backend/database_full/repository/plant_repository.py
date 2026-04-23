"""Репозиторий для работы с растениями"""
from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class PlantRepository(BaseRepository):
    """Репозиторий для таблиц plant_templates и user_plants"""

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Получить все шаблоны растений"""
        return self.db.execute_query("""
            SELECT species_id, species_name, nickname, description, character_trait,
                   water_interval_min, water_interval_max, light_requirement, humidity_preference,
                   watering_advice, light_advice, flowering_conditions, temp_advice,
                   tips, symptoms, sort_order
            FROM plant_templates 
            ORDER BY sort_order
        """)

    def get_template_by_species_id(self, species_id: int) -> Optional[Dict[str, Any]]:
        """Получить шаблон по species_id"""
        result = self.db.execute_query(
            "SELECT * FROM plant_templates WHERE species_id = ?",
            (species_id,)
        )
        return result[0] if result else None

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Получить шаблон по ID"""
        return self.get_by_id("plant_templates", "id", template_id)

    def create_user_plant(self, plant_id: str, user_id: str, template_id: str, custom_name: str) -> bool:
        """Создать растение пользователя"""
        return self.db.execute_update("""
            INSERT INTO user_plants (id, user_id, template_id, custom_name, growth_stage)
            VALUES (?, ?, ?, ?, 'seed')
        """, (plant_id, user_id, template_id, custom_name))

    def get_user_plants(self, user_id: str, only_alive: bool = True) -> List[Dict[str, Any]]:
        """Получить растения пользователя"""
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
        """Получить растение пользователя по ID"""
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
        """Полить растение"""
        return self.db.execute_update("""
            UPDATE user_plants SET last_watered = CURRENT_DATE, last_checked = CURRENT_DATE WHERE id = ?
        """, (plant_id,))

    def update_health_status(self, plant_id: str, status: str) -> bool:
        """Обновить статус здоровья"""
        return self.db.execute_update(
            "UPDATE user_plants SET health_status = ? WHERE id = ?",
            (status, plant_id)
        )

    def update_growth(self, plant_id: str, growth_stage: str, growth_progress: float) -> bool:
        """Обновить стадию роста и прогресс"""
        return self.db.execute_update("""
            UPDATE user_plants SET growth_stage = ?, growth_progress = ? WHERE id = ?
        """, (growth_stage, growth_progress, plant_id))

    def increment_growth_progress(self, plant_id: str, increment: float) -> bool:
        """Увеличить прогресс роста"""
        return self.db.execute_update("""
            UPDATE user_plants SET growth_progress = growth_progress + ? WHERE id = ?
        """, (increment, plant_id))

    def kill_plant(self, plant_id: str, cause: str) -> bool:
        """Убить растение"""
        return self.db.execute_update("""
            UPDATE user_plants 
            SET is_alive = 0, death_cause = ?, death_date = CURRENT_DATE, times_reborn = times_reborn + 1
            WHERE id = ?
        """, (cause, plant_id))

    def revive_plant(self, plant_id: str) -> bool:
        """Воскресить растение"""
        return self.db.execute_update("""
            UPDATE user_plants 
            SET is_alive = 1, health_status = 'healthy', growth_stage = 'seed', growth_progress = 0,
                death_cause = NULL, death_date = NULL, last_watered = CURRENT_DATE, last_checked = CURRENT_DATE
            WHERE id = ?
        """, (plant_id,))

    def increment_times_flowered(self, plant_id: str) -> bool:
        """Увеличить счётчик цветений"""
        return self.db.execute_update(
            "UPDATE user_plants SET times_flowered = times_flowered + 1 WHERE id = ?",
            (plant_id,)
        )

    def get_dead_plants(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить умершие растения пользователя"""
        return self.db.execute_query("""
            SELECT up.*, pt.species_name, pt.nickname as plant_nickname, up.death_cause
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.user_id = ? AND up.is_alive = 0
            ORDER BY up.death_date DESC
        """, (user_id,))