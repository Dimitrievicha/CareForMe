"""
Репозиторий для синхронизации состояния игры
"""

from typing import Optional, Dict, Any
from .base_repository import BaseRepository
import json


class GameRepository(BaseRepository):
    """Репозиторий для таблицы game_states."""

    def save_game_state(self, user_id: str, slot_data: dict, current_level: int, achievements: dict,
                        updated_at: str) -> bool:
        """Сохранить состояние игры."""
        return self.db.execute_update("""
            INSERT OR REPLACE INTO game_states (user_id, slot_data, current_level, achievements, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            json.dumps(slot_data),
            current_level,
            json.dumps(achievements),
            updated_at
        ))

    def load_game_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Загрузить состояние игры."""
        result = self.db.execute_query("""
            SELECT slot_data, current_level, achievements FROM game_states 
            WHERE user_id = ?
        """, (user_id,))

        if result and len(result) > 0:
            return {
                'slotData': json.loads(result[0]['slot_data']) if result[0]['slot_data'] else {},
                'currentLevel': result[0]['current_level'],
                'achievements': json.loads(result[0]['achievements']) if result[0]['achievements'] else {}
            }
        return None