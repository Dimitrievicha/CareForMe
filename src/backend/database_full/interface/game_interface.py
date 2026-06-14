"""
Интерфейс для синхронизации состояния игры
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..repository.game_repository import GameRepository
from ..service.room_game_service import room_game_service


class GameInterface:
    """Интерфейс для работы c game_states и игровой логикой комнаты."""

    def __init__(self):
        self._repo = GameRepository()
        self._room = room_game_service

    def save_state(self, user_id: str, slot_data: dict, current_level: int, achievements: dict) -> bool:
        """Сохранить состояние игры."""
        return self._repo.save_game_state(
            user_id, slot_data, current_level, achievements, datetime.now().isoformat()
        )

    def load_state(self, user_id: str) -> Dict[str, Any]:
        """Загрузить состояние игры."""
        return self._repo.load_game_state(user_id) or {'slotData': {}, 'currentLevel': 1, 'achievements': {}}

    def water_slot(self, user_id: str, slot_name: str) -> Dict[str, Any]:
        return self._room.water_slot(user_id, slot_name)

    def plant_in_slot(self, user_id: str, slot_name: str, species_id: int) -> Dict[str, Any]:
        return self._room.plant_in_slot(user_id, slot_name, species_id)

    def tick(self, user_id: str, slot_names: Optional[List[str]] = None) -> Dict[str, Any]:
        return self._room.tick(user_id, slot_names)

    def move_slot(self, user_id: str, from_slot: str, to_slot: str) -> Dict[str, Any]:
        return self._room.move_slot(user_id, from_slot, to_slot)

    def mark_read_description(self, user_id: str) -> Dict[str, Any]:
        return self._room.mark_read_description(user_id)


game_interface = GameInterface()
