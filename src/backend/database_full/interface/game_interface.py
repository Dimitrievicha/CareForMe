"""
Интерфейс для синхронизации состояния игры
"""

from ..repository.game_repository import GameRepository


class GameInterface:
    """Интерфейс для работы TESTING_REPORT.md game_states."""

    def __init__(self):
        self._repo = GameRepository()

    def save_state(self, user_id: str, slot_data: dict, current_level: int, achievements: dict) -> bool:
        """Сохранить состояние игры."""
        from datetime import datetime
        return self._repo.save_game_state(
            user_id, slot_data, current_level, achievements, datetime.now().isoformat()
        )

    def load_state(self, user_id: str) -> dict:
        """Загрузить состояние игры."""
        result = self._repo.load_game_state(user_id)
        if result:
            return result
        return {'slotData': {}, 'currentLevel': 1, 'achievements': {}}


game_interface = GameInterface()