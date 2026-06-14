"""
Репозиторий для работы с советами.
Таблицы: tips, plant_templates.
"""

from typing import List, Dict, Any, Optional
from .base_repository import BaseRepository


class TipsRepository(BaseRepository):
    """Репозиторий для таблиц tips и plant_templates (советы)."""

    def get_all_tips(self) -> List[Dict[str, Any]]:
        """Все советы, отсортированные по id."""
        return self.db.execute_query(
            "SELECT id, tip_type, title, message, is_positive FROM tips ORDER BY id"
        )

    def get_positive_tips(self) -> List[Dict[str, Any]]:
        """Позитивные советы."""
        return self.db.execute_query(
            "SELECT id, tip_type, title, message FROM tips WHERE is_positive = 1 ORDER BY id"
        )

    def get_tip_by_type(self, tip_type: str) -> Optional[Dict[str, Any]]:
        """Первый совет указанного типа."""
        result = self.db.execute_query(
            "SELECT id, title, message, is_positive FROM tips WHERE tip_type = ? LIMIT 1",
            (tip_type,)
        )
        return result[0] if result else None

    def get_plant_template(self, species_id: int) -> Optional[Dict[str, Any]]:
        """Советы и симптомы для растения по species_id."""
        result = self.db.execute_query(
            "SELECT species_name, tips, symptoms FROM plant_templates WHERE species_id = ?",
            (species_id,)
        )
        return result[0] if result else None