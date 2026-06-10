"""
Репозиторий для работы TESTING_REPORT.md растениями.

Содержит методы для работы TESTING_REPORT.md таблицами:
    - plant_templates: шаблоны растений (справочник)
    - user_plants: растения конкретных пользователей
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from .base_repository import BaseRepository


class PlantRepository(BaseRepository):
    """
    Репозиторий для таблиц plant_templates и user_plants.

    Обрабатывает все операции TESTING_REPORT.md растениями:
        - Получение шаблонов растений
        - Посадка, полив, рост, смерть растений
        - Статистика по растениям
    """

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """
        Получает все шаблоны растений, отсортированные по sort_order.
        """
        return self.db.execute_query("""
            SELECT species_id, species_name, nickname, description, character_trait,
                   disease, why_disease,
                   water_interval_min, water_interval_max,
                   light_requirement, humidity_preference,
                   watering_advice, light_advice, tips, symptoms, flowering_conditions,
                   unlock_level, sort_order
            FROM plant_templates 
            ORDER BY sort_order
        """)

    def get_template_by_species_id(self, species_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает шаблон растения по species_id.

        Args:
            species_id: ID вида растения
                1 = Спатифиллум (Женское счастье)
                2 = Кактус (Корифанта)
                3 = Фикус (Бенджамина)

        Returns:
            Данные шаблона или None
        """
        return self.get_one_by_field("plant_templates", "species_id", species_id)

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает шаблон растения по внутреннему UUID.

        Args:
            template_id: UUID шаблона (первичный ключ)

        Returns:
            Данные шаблона или None
        """
        return self.get_by_id("plant_templates", "id", template_id)

    def create_user_plant(self, plant_id: str, user_id: str,
                          template_id: str, custom_name: str) -> bool:
        """
        Создает новое растение пользователя (посадка).

        Args:
            plant_id: UUID нового растения (генерируется заранее)
            user_id: ID пользователя
            template_id: ID шаблона растения
            custom_name: Пользовательское имя растения

        Returns:
            True при успехе
        """
        return self.insert("user_plants", {
            "id": plant_id,
            "user_id": user_id,
            "template_id": template_id,
            "custom_name": custom_name,
            "growth_stage": "seed",
            "last_watered": date.today().isoformat(),
            "last_checked": date.today().isoformat()
        })

    def get_user_plants(self, user_id: str, only_alive: bool = True) -> List[Dict[str, Any]]:
        """
        Получает растения пользователя TESTING_REPORT.md данными из шаблона.

        Args:
            user_id: ID пользователя
            only_alive: Если True, только живые растения (is_alive = 1)

        Returns:
            Список растений TESTING_REPORT.md JOIN-данными из plant_templates

        Returns структура:
            [
                {
                    "id": "uuid",
                    "custom_name": "Мой кактус",
                    "health_status": "healthy",
                    "growth_stage": "growing",
                    "species_name": "Кактус Корифанта",
                    "water_interval_min": 3,
                    "water_interval_max": 10,
                    ...
                }
            ]
        """
        alive_filter = "AND up.is_alive = 1" if only_alive else ""

        return self.db.execute_query(f"""
            SELECT up.*, 
                   pt.species_name, 
                   pt.water_interval_min, 
                   pt.water_interval_max, 
                   pt.light_requirement,
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.user_id = ? {alive_filter}
            ORDER BY up.acquired_at DESC
        """, (user_id,))

    def get_user_plant_by_id(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает конкретное растение пользователя по UUID.

        Args:
            plant_id: UUID растения

        Returns:
            Данные растения TESTING_REPORT.md JOIN-полями из шаблона или None
        """
        result = self.db.execute_query("""
            SELECT up.*, 
                   pt.species_name, 
                   pt.water_interval_min, 
                   pt.water_interval_max, 
                   pt.light_requirement,
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.id = ?
        """, (plant_id,))
        return result[0] if result else None

    def water_plant(self, plant_id: str) -> bool:
        """
        Поливает растение - обновляет дату последнего полива.

        Также обновляет статус здоровья на 'healthy', если он был плохим.

        Args:
            plant_id: UUID растения

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants 
            SET last_watered = CURRENT_DATE, 
                last_checked = CURRENT_DATE,
                health_status = 'healthy'
            WHERE id = ?
        """, (plant_id,))

    def update_health_status(self, plant_id: str, status: str) -> bool:
        """
        Обновляет статус здоровья растения.

        Args:
            plant_id: UUID растения
            status: Статус здоровья
                - healthy: здоров
                - wilting: увядает (пора поливать)
                - overwatered: перелит
                - dying: умирает (срочно полить)
                - dead: мертв

        Returns:
            True при успехе
        """
        return self.update("user_plants", "id", plant_id, {
            "health_status": status
        })

    def update_growth(self, plant_id: str, growth_stage: str, growth_progress: float) -> bool:
        """
        Обновляет стадию роста и прогресс.

        Args:
            plant_id: UUID растения
            growth_stage: Стадия развития
                - seed: семечко (0%)
                - seedling: росток (25%)
                - growing: растет (50%)
                - mature: взрослое (75%)
                - flowering: цветет (100%)
            growth_progress: Прогресс в процентах (0-100)

        Returns:
            True при успехе
        """
        return self.update("user_plants", "id", plant_id, {
            "growth_stage": growth_stage,
            "growth_progress": growth_progress
        })

    def increment_growth_progress(self, plant_id: str, increment: float) -> bool:
        """
        Увеличивает прогресс роста на указанное значение.

        Args:
            plant_id: UUID растения
            increment: Прирост прогресса (обычно 5-20% в зависимости от здоровья)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants 
            SET growth_progress = growth_progress + ? 
            WHERE id = ?
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
        return self.update("user_plants", "id", plant_id, {
            "has_perfect_growth": True
        })

    def increment_times_flowered(self, plant_id: str) -> bool:
        """
        Увеличивает счетчик цветений растения.

        Вызывается каждый раз, когда растение достигает стадии 'flowering'.

        Args:
            plant_id: UUID растения

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants SET times_flowered = times_flowered + 1 
            WHERE id = ?
        """, (plant_id,))

    def kill_plant(self, plant_id: str, cause: str) -> bool:
        """
        Помечает растение как мертвое.

        Args:
            plant_id: UUID растения
            cause: Причина смерти
                - drought: засуха (не поливали слишком долго)
                - overwater: перелив (поливали слишком часто)
                - neglect: запустение (комбинация факторов)

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants 
            SET is_alive = 0, 
                death_cause = ?, 
                death_date = CURRENT_DATE, 
                times_reborn = times_reborn + 1
            WHERE id = ?
        """, (cause, plant_id))

    def revive_plant(self, plant_id: str) -> bool:
        """
        Воскрешает мертвое растение - пересаживает заново.

        Сбрасывает все параметры к начальным (как при посадке).

        Args:
            plant_id: UUID растения

        Returns:
            True при успехе
        """
        return self.db.execute_update("""
            UPDATE user_plants 
            SET is_alive = 1, 
                health_status = 'healthy', 
                growth_stage = 'seed', 
                growth_progress = 0, 
                death_cause = NULL, 
                death_date = NULL, 
                last_watered = CURRENT_DATE, 
                last_checked = CURRENT_DATE
            WHERE id = ?
        """, (plant_id,))

    def get_dead_plants(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает мертвые растения пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список мертвых растений TESTING_REPORT.md причиной смерти, отсортированные по дате смерти
        """
        return self.db.execute_query("""
            SELECT up.*, pt.species_name, up.death_cause
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

    def update_light_level(self, plant_id: str, light_level: str) -> bool:
        """Обновить уровень освещения растения."""
        return self.db.execute_update(
            "UPDATE user_plants SET current_light_level = ? WHERE id = ?",
            (light_level, plant_id)
        )

    def update_location(self, plant_id: str, location: str) -> bool:
        """Обновить локацию растения."""
        return self.db.execute_update(
            "UPDATE user_plants SET location = ? WHERE id = ?",
            (location, plant_id)
        )

    def get_plants_by_species(self, user_id: str, species_id: int) -> List[Dict[str, Any]]:
        """
        Получает растения пользователя по виду.

        Args:
            user_id: ID пользователя
            species_id: ID вида растения

        Returns:
            Список растений указанного вида
        """
        return self.db.execute_query("""
            SELECT up.*, pt.species_name
            FROM user_plants up
            JOIN plant_templates pt ON up.template_id = pt.id
            WHERE up.user_id = ? AND pt.species_id = ? AND up.is_alive = 1
        """, (user_id, species_id))

    def count_user_plants(self, user_id: str, only_alive: bool = True) -> int:
        """
        Подсчитывает количество растений пользователя.

        Args:
            user_id: ID пользователя
            only_alive: Считать только живые растения

        Returns:
            Количество растений
        """
        alive_filter = "is_alive = 1" if only_alive else ""
        return self.count("user_plants",
                          f"user_id = ? AND {alive_filter}" if only_alive else "user_id = ?",
                          (user_id,))