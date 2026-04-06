from dataclasses import dataclass
from datetime import date
import uuid
from typing import Optional

@dataclass
class UserChallenge:
    """Прогресс игрока по достижению"""
    user_id: uuid.UUID
    challenge_id: uuid.UUID
    current_progress: int = 0
    is_completed: bool = False  # Заменил score_challenge
    completed_at: Optional[date] = None