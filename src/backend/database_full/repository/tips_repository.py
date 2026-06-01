"""
Репозиторий для работы с советами
"""

from typing import List, Dict, Any, Optional
from .base_repository import BaseRepository


class TipsRepository(BaseRepository):
    """Репозиторий для таблиц tips и plant_templates."""

    def get_all_tips(self) -> List[tuple]:
        """Получить все советы."""
        return self.db.execute_query(
            "SELECT id, tip_type, title, message, is_positive FROM tips ORDER BY id"
        )

    def get_positive_tips(self) -> List[tuple]:
        """Получить позитивные советы."""
        return self.db.execute_query(
            "SELECT id, tip_type, title, message FROM tips WHERE is_positive = 1 ORDER BY id"
        )

    def get_tip_by_type(self, tip_type: str) -> Optional[List[tuple]]:
        """Получить совет по типу."""
        return self.db.execute_query(
            "SELECT id, title, message, is_positive FROM tips WHERE tip_type = ? LIMIT 1",
            (tip_type,)
        )

    def get_plant_template(self, species_id: int) -> Optional[List[tuple]]:
        """Получить шаблон растения."""
        return self.db.execute_query(
            "SELECT species_name, tips, symptoms FROM plant_templates WHERE species_id = ?",
            (species_id,)
        )